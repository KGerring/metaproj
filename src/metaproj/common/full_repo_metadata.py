#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from collections import defaultdict
from itertools import chain, islice
from logging import Handler, Logger, LogRecord, getLogger
from subprocess import TimeoutExpired
from typing import TYPE_CHECKING, DefaultDict, Dict, Iterable, List, Mapping, Optional, Set, Type

import click
from attr import dataclass, field
from fixit.cli.utils import print_yellow
from libcst.metadata import FullRepoManager, FullyQualifiedNameProvider, ProviderT, TypeInferenceProvider

from .base import CstLintRule
from .utils import LintRuleCollectionT

if TYPE_CHECKING:
    from logging import Handler, Logger, LogRecord, getLogger
    from libcst.metadata.base_provider import ProviderT

BATCH_SIZE: int = 100
PLACEHOLDER_CACHES: Dict[ProviderT, object] = {
    TypeInferenceProvider: {"types": []},
    FullyQualifiedNameProvider: {},
}

# run_command, TypeInferenceProvider
# mgr = FullRepoManager(".", {"rule_lint_engine.py"}, {FullyQualifiedNameProvider, TypeInferenceProvider})
# wrapper = mgr.get_metadata_wrapper_for_path("rule_lint_engine.py")
# fqnames = wrapper.resolve(FullyQualifiedNameProvider)
# {type(k): v for (k, v) in fqnames.items()}
# params = ",".join(f"path='{root_path / path}'" for path in paths)
# cmd_args = ["pyre", "--noninteractive", "query", f'"types({params})"']
# PyreData, types(path='path')


@dataclass(frozen=False)
class FullRepoMetadataConfig:
    """
    Class used with :class:`libcst.metadata.FullRepoManager`
        config.repo_root_dir


    """

    #  `Set[Type[meta.base_provider.BaseMetadataProvider[object]]]`; used as
    #  `frozenset[Variable[_T_co](covariant)]`.
    providers: Set[ProviderT] = field(

        default=frozenset([TypeInferenceProvider, FullyQualifiedNameProvider])
    )
    timeout_seconds: int = 10
    repo_root_dir: str = ""
    batch_size: int = BATCH_SIZE
    logger: Optional[Logger] = None


def get_repo_caches(
    paths: Iterable[str],
    config: FullRepoMetadataConfig,
) -> Mapping[str, Dict[ProviderT, object]]:
    """
    Generate type metadata by instantiating a :class:`~libcst.metadata.FullRepoManager` with
    :class:`~libcst.metadata.FullRepoManager` passed to ```providers``` parameter.

    :param paths: An iterable of paths to files to pass to :class:`~libcst.metadata.FullRepoManager` constructor's
    `paths` argument.
        These will be split in batches where the combined length of each path
        in the batch is <= `arg_size`.

    :param timeout: The number of seconds at which to cap the pyre query which is run as a subprocess during cache resolving.

    :param repo_root_dir: Root directory of paths in ```paths```.

    :param batch_size: The size of the batch of paths to pass in each call to
        the `FullRepoManager` constructor.

    # We want to fail silently since some metadata providers can be flaky. If a logger is provided by the caller, we'll add a log here.
    # Populate with placeholder caches to avoid failures down the line. This will however result in reduced functionality in cache-dependent lint rules.

    # TODO: remove access of private variable when public `cache` property is
        available in libcst.metadata.FullRepoManager API.

    misc:
    the cache from frm._cache is mapping of mappings of
        `provider` to _path-cache mapping `so Dict[provider, files]`
            where `files` is a Dict[_path, cache] itself` to make the

        batch_caches[_path][provider] = cache to update as a fallback

    >>> mgr = FullRepoManager('/Users/kristen/repos/Fixit',{"fixit/common/base.py"}, {FullyQualifiedNameProvider, TypeInferenceProvider})
    >>> wrapper: meta.MetadataWrapper = mgr.get_metadata_wrapper_for_path("fixit/common/base.py")
    >>> fqnames = wrapper.resolve(meta.FullyQualifiedNameProvider)
    >>> cache = mgr.get_cache_for_path("fixit/common/base.py")
    #pyre --noninteractive query "types(path='fixit/common/base.py')"
    #_cache: Dict["ProviderT", files= Mapping[str, object]] = {}

    """
    caches = {}
    paths_iter = iter(paths)
    head: Optional[str] = next(paths_iter, None)
    while head is not None:
        paths_batch = tuple(chain([head], islice(paths_iter, config.batch_size - 1)))
        head = next(paths_iter, None)
        frm = FullRepoManager(
            repo_root_dir=config.repo_root_dir,
            paths=paths_batch,
            providers=config.providers,
            timeout=config.timeout_seconds,
        )
        try:
            frm.resolve_cache()
        except Exception:
            # We want to fail silently since some metadata providers can be flaky. If a logger is provided by the caller, we'll add a log here.
            logger = config.logger
            if logger is not None:
                logger.warning(
                    "Failed to retrieve metadata cache.",
                    exc_info=True,
                    extra={"paths": paths_batch},
                )
            # Populate with placeholder caches to avoid failures down the line. This will however result in reduced functionality in cache-dependent lint rules.

            caches.update(
                dict.fromkeys(
                    paths_batch,
                    {provider: PLACEHOLDER_CACHES[provider] for provider in config.providers},
                )
            )
        else:
            # TODO: remove access of private variable when public `cache` property is available in libcst.metadata.FullRepoManager API.
            batch_caches = defaultdict(dict)
            for provider, files in frm._cache.items():
                for _path, cache in files.items():
                    batch_caches[_path][provider] = cache
            caches.update(batch_caches)
    return caches


class MetadataCacheErrorHandler(Handler):
    timeout_paths: List[str] = []
    other_exceptions: DefaultDict[Type[Exception], List[str]] = defaultdict(list)

    def emit(self, record: LogRecord) -> None:
        # According to logging documentation, exc_info will be a tuple of three values: (type, value, traceback)
        # see https://docs.python.org/3.8/library/logging.html#logrecord-objects
        exc_info = record.exc_info
        if exc_info is not None:
            exc_type = exc_info[0]
            failed_paths = record.__dict__.get("paths")
            if exc_type is not None:
                # Store exceptions in memory for processing later.
                if exc_type is TimeoutExpired:
                    self.timeout_paths += failed_paths
                else:
                    self.other_exceptions[exc_type] += failed_paths

def metadata_caches_filter(rule: CstLintRule) -> bool:
    return issubclass(rule, CstLintRule) and getattr(rule, "requires_metadata_caches")()

def rules_require_metadata_cache(
        rules: LintRuleCollectionT
) -> bool:
    return any(issubclass(r, CstLintRule) and getattr(r, "requires_metadata_caches")() for r in rules)


def get_metadata_caches(cache_timeout: int,
                        file_paths: Iterable[str]
                        ) -> Mapping[str, Mapping[ProviderT, object]]:
    """
    Returns a metadata cache for each file in ``file_paths``.
    # Let user know of any cache retrieval failures.

    """
    logger: Logger = getLogger("Metadata Caches Logger")
    handler = MetadataCacheErrorHandler()
    logger.addHandler(handler)
    full_repo_metadata_config: FullRepoMetadataConfig = FullRepoMetadataConfig(

        providers={TypeInferenceProvider, FullyQualifiedNameProvider},
        timeout_seconds=cache_timeout,
        batch_size=100,
        logger=logger,
    )

    metadata_caches = get_repo_caches(file_paths, full_repo_metadata_config)
    # Let user know of any cache retrieval failures.
    if handler.timeout_paths:
        click.secho(
            "Unable to get metadata cache for the following paths:\n" + "\n".join(handler.timeout_paths),
            fg="magenta",
        )
        print_yellow("Try increasing the --cache-timeout value or passing fewer files.")
    for k, v in handler.other_exceptions.items():
        print(f"Encountered exception {k} for the following paths:\n" + "\n".join(v))
        print_yellow("Running `pyre start` may solve the issue.")
    return metadata_caches

__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if ((callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper()) and not getattr(v, "__name__", k).startswith("__"))  # callables from this module  # or CONSTANTS
    ]
)  # neither marked internal
