#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = tasks
# author=KGerring
# date = 4/10/21
# project poetryproj
# docs root
"""
 poetryproj  


@task
def setup(c, clean=False):
	if clean:
        c.run("rm -rf target")
        ### ... setup things here ...
    c.run("tar czvf target.tgz target")
    

@task(pre=[setup])
def build(c):
	c.run("build, accounting for leftover files...")

@task(pre=[call(setup, clean=True)])
def clean_build(c):
	c.run("build, assuming clean slate...")
 


"""
from __future__ import annotations
import sys
import os
from invoke import Task, task, Collection
from invoke.tasks import Call, call
from invoke.util import log
from invoke import run
from pathlib import Path

root = Path.cwd().parent.resolve()
# from invocations import testing, checks, docs, pytest, autodoc, util
# from invocations.docs import doctest, tree


@task()
def releases_info(c):
    """show sphinx releases=stff (test)

    :param c:
    :type c:
    :return:
    :rtype:

    """
    print("releases.util.changelog2dict")
    print("releases.util.make_app")
    print(
        """
	
	:param c:
	:type c:
	:return:
	:rtype:
	
	
	releases.util.parse_changelog(path, **kwargs)
	releases.util.load_conf(srcdir)
	releases.util.make_app(**kwargs)
	releases.util.changelog2dict(changelog)
	
	
	__init__:
		releases.generate_changelog(app, doctree)
		
		
	
	models:
		Release
		Issue
		Version
		
	line_manager:
		LineManager
	
	"""
    )


DEFAULT_ISORT_SETTINGS = {
    "add_imports": ["from __future__ import annotations"],
    "float_to_top": True,
    "multi_line_output": 3,
    "force_single_line": True,
    "include_trailing_comma": True,
    "force_grid_wrap": 0,
    "use_parentheses": True,
    "ensure_newline_before_comments": True,
    "line_length": 120,
}


@task(name="run_isort", iterable=["files"], default=True)
def run_isort(c, files=None):
    """
    Run isort specific on files
    :param c:
    :type c:
    :param files:
    :type files:
    :return:
    :rtype:
    """
    if not files:
        filearg = "."
    else:
        filearg = " ".join(files)
    c.run(
        f'isort -m 3 --sl --float-to-top -a "from __future__ import annotations" -l 120 --use-parentheses --trailing-comma {filearg}'
    )


@task(name="blacken", iterable=["folders"])
def blacken(
    c, line_length=79, folders=None, check=False, diff=False, find_opts=None
):
    r"""
    Run black on the current source tree (all ``.py`` files).

    .. warning::
            ``black`` only runs on Python 3.6 or above. (However, it can be
            executed against Python 2 compatible code.)

    :param int line_length:
            Line length argument. Default: ``79``.
    :param list folders:
            List of folders (or, on the CLI, an argument that can be given N times)
            to search within for ``.py`` files. Default: ``["."]``. Honors the
            ``blacken.folders`` config option.
    :param bool check:
            Whether to run ``black --check``. Default: ``False``.
    :param bool diff:
            Whether to run ``black --diff``. Default: ``False``.
    :param str find_opts:
            Extra option string appended to the end of the internal ``find``
            command. For example, skip a vendor directory with ``"-and -not -path
            ./vendor\*"``, add ``-mtime N``, or etc. Honors the
            ``blacken.find_opts`` config option.

    .. versionadded:: 1.2
    .. versionchanged:: 1.4
            Added the ``find_opts`` argument.
    """
    config = c.config.get("blacken", {})
    default_folders = ["."]
    configured_folders = config.get("folders", default_folders)
    folders = folders or configured_folders

    default_find_opts = ""
    configured_find_opts = config.get("find_opts", default_find_opts)
    find_opts = find_opts or configured_find_opts

    black_command_line = "black -l {}".format(line_length)
    if check:
        black_command_line = "{} --check".format(black_command_line)
    if diff:
        black_command_line = "{} --diff".format(black_command_line)
    if find_opts:
        find_opts = " {}".format(find_opts)
    else:
        find_opts = ""

    cmd = "find {} -name '*.py'{} | xargs {}".format(
        " ".join(folders), find_opts, black_command_line
    )
    c.run(cmd, pty=True)


@task
def clean():
    """clean - remove build artifacts.

    ``from plumbum.cmd import find, gfind``


    """
    run("rm -rf build/")
    run("rm -rf dist/")
    run("rm -rf pyselector.egg-info")
    run("find . -name __pycache__ -delete")
    run("find . -name *.pyc -delete")
    run("find . -name *.pyo -delete")
    run("find . -name *~ -delete")
    log.info("cleaned up")


@task
def lint():
    """lint - check style with flake8.

    from plumbum.cmd import flake8


    """
    run("flake8 {{ package }} tests")


BUMPVERSION_CONFIG_FILE = root / ".bumpversion.cfg"


@task(
    help={
        "param": "The parameter name to bump; can be one of `{major}.{minor}.{patch}"
    }
)
def bumpversion(c, param="minor"):
    """
    #. f'bumpversion --dry-run --list {param} | grep new_version | sed -r s,"^.*=",, '

    # parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\-(?P<release>[a-z]+))?
    # serialize = {major}.{minor}.{patch}
    # --config-file
    :param c:
    :param param: The section to bump; default is 'minor'
    :return:
    """
    c.run(
        f'bumpversion --dry-run --list {param} | grep new_version | sed -r s,"^.*=",, '
    )


@task
def bumpversion_fromfile(c, part="minor", configfile=BUMPVERSION_CONFIG_FILE):
    """
    Like usual bumpversion but read from the .bumpversion.cfg file that is ../HERE (under _init.py).
    :param c:
    :param part: The part to bump. One of 'major.minor.patch`
    :param configfile: The path to read deafults from `../.bumpversion.cfg`
    :return:
    """
    c.run(
        f'bumpversion --config-file={BUMPVERSION_CONFIG_FILE} --dry-run --list {param} | grep new_version | sed -r s,"^.*=",, '
    )


@task
def remove_pycache(c, src = root):
    """
    search for `__pycache__` directories and delete them
    :param c:
    :param path: path to start searching
    :return:
    """
    if src is None:
        src = str(root)
    c.run("find {} -name __pycache__ -type d -print0 | sudo xargs -0 /bin/rm -fr".format(src))

@task
def find_pycache(c, path=None):
    """
    :param c:
    :param path: path to start searching
    :return:
    """
    if path is None:
        path = c.gfind.path
    c.run(
        "find {} -name __pycache__ -type d -print0 | xargs -0 -n 1".format(path)
    )


__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if (
            (
                callable(v)
                and getattr(v, "__module__", "")
                == __name__  # callables from this module
                or k.isupper()
            )
            and not str(getattr(v, "__name__", k)).startswith(  # or CONSTANTS
                "__"
            )
        )
    ]
)  # neither marked internal

if __name__ == "__main__":
    print(__file__)
