
"""Files and folders in a project are represented as resource objects.

Files and folders are access through `Resource` objects. `Resource` has
two subclasses: `File` and `Folder`. What we care about is that
refactorings and `change.Change`s use resources.

There are two options to create a `Resource` for a path in a project.
Note that in these examples `path` is the path to a file or folder
relative to the project's root. A project's root folder is represented
by an empty string.

  1) Use the `Project.get_resource()` method. E.g.:

       myresource = myproject.get_resource(path)


  2) Use the `libutils` module. `libutils` has a function
     named `path_to_resource()`. It takes a project and a path:

       from . import libutils

       myresource = libutils.path_to_resource(myproject, path)

Once we have a `Resource`, we can retrieve information from it, like
getting the path relative to the project's root (via `path`), reading
from and writing to the resource, moving the resource, etc.
"""

from __future__ import annotations

import os
import re

from . import change, exceptions, fscommands
from .change import ChangeContents, ChangeSet
from .resources import File, Folder, Resource, _ResourceMatcher


class ChangeStack:
    def __init__(self, project, description="merged changes"):
        self.project = project
        self.description = description
        self.stack = []

    def push(self, changes):
        self.stack.append(changes)
        self.project.do(changes)

    def pop_all(self):
        for i in range(len(self.stack)):
            self.project.history.undo(drop=True)

    def merged(self):
        result = change.ChangeSet(self.description)
        for changes in self.stack:
            for c in self._basic_changes(changes):
                result.add_change(c)
        return result

    def _basic_changes(self, changes):
        if isinstance(changes, change.ChangeSet):
            for child in changes.changes:
                for atom in self._basic_changes(child):
                    yield atom
        else:
            yield changes


CS_DOC(
    """For performing many refactorings as a single command

`changestack` module can be used to perform many refactorings on top
of each other as one bigger command.  It can be used like::

  stack = ChangeStack(project, 'my big command')

  #..
  stack.push(refactoring1.get_changes())
  #..
  stack.push(refactoring2.get_changes())
  #..
  stack.push(refactoringX.get_changes())

  stack.pop_all()
  changes = stack.merged()

Now `changes` can be previewed or performed as before.
"""
)

__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if ((callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper()) and not getattr(v, "__name__", k).startswith("__"))  # callables from this module  # or CONSTANTS
    ]
)  # neither marked internal


