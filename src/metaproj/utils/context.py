"""

"""
from __future__ import annotations

import contextlib
import threading
from contextlib import contextmanager
from typing import Any
from typing import Iterator
from typing import MutableMapping

from .utils.collection import Config
from .utils.collection import DotDict
from .utils.collection import config
from .utils.collection import merge_dicts


class Context(DotDict, threading.local):
    """
    A thread safe context store for Prefect data.

    The `Context` is a `DotDict` subclass, and can be instantiated the same way.

    Args:
        - *args (Any): arguments to provide to the `DotDict` constructor (e.g.,
            an initial dictionary)
        - **kwargs (Any): any key / value pairs to initialize this context with
    # Initialize with config context
    init = {}
    init.update(config.get("context", {}))
    # Overwrite with explicit args
    init.update(dict(*args, **kwargs))
    init["config"] = merge_dicts(config, init.get("config", {}))

    """
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        init = {}
        # Initialize with config context
        init.update(config.get("context", {}))
        # Overwrite with explicit args
        init.update(dict(*args, **kwargs))
        # Merge in config (with explicit args overwriting)
        init["config"] = merge_dicts(config, init.get("config", {}))
        super().__init__(init)
    
    def __getstate__(self) -> None:
        """
        Because we dynamically update context during runs, we don't ever want to pickle
        or "freeze" the contents of context.  Consequently it should always be accessed
        as an attribute of the module.
        """
        raise TypeError(
            "Pickling context objects is explicitly not supported. You should always " "access context as an attribute of the `fixit` module, as in `prefect.context`")
    
    def __repr__(self) -> str:
        return "<Context>"
    
    @contextlib.contextmanager
    def __call__(self, *args: T_MutableMapping, **kwargs: Any) -> Iterator[Context]:
        """
        A context manager for setting / resetting the Prefect context

        Example:
            import prefect.context
            with prefect.context(dict(a=1, b=2), c=3):
                print(prefect.context.a) # 1
        """
        # Avoid creating new `Context` object, copy as `dict` instead.
        previous_context = self.__dict__.copy()
        try:
            new_context = dict(*args, **kwargs)
            if "config" in new_context:
                new_context["config"] = merge_dicts(self.get("config", {}), new_context["config"])
            self.update(new_context)  # type: ignore
            yield self
        finally:
            self.clear()
            self.update(previous_context)

context = Context()

@contextmanager
def set_temporary_config(temp_config: dict) -> Iterator:
    """
    Temporarily sets configuration values for the duration of the context manager.

    :param dict temp_config: a dictionary containing (possibly nested) configuration keys and
            values. Nested configuration keys should be supplied as `.`-delimited strings.

    .. :code-block: python
    >>> with set_temporary_config({'setting': 1, 'nested.setting': 2}):
        assert config.setting == 1
        assert config.nested.setting == 2

    """
    try:
        old_config = config.copy()
        for key, value in temp_config.items():
            # the `key` might be a dot-delimited string, so we split on "." and set the value
            cfg = config
            subkeys = key.split(".")
            for subkey in subkeys[:-1]:
                cfg = cfg.setdefault(subkey, Config())
            cfg[subkeys[-1]] = value
        # ensure the new config is available in context
        with prefect.context(config=config):
            yield config
    finally:
        config.clear()
        config.update(old_config)


__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if ((callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper()) and not str(getattr(v, "__name__", k)).startswith("__"))  # callables from this module  # or CONSTANTS
    ]
)  # neither marked internal
