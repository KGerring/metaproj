#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = no_typed_dict_rule
# author=KGerring
# date = 4/21/21
# project poetryproj
# docs root
"""
 poetryproj  

"""
from __future__ import annotations

import os
import sys
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import libcst as cst
from fixit import CstLintRule
from fixit import InvalidTestCase as Invalid
from fixit import ValidTestCase as Valid
# from . import no_namedtuple
# from .no_namedtuple import NoNamedTupleRule
from libcst import MaybeSentinel
from libcst import ensure_type
from libcst import parse_expression
from libcst.metadata import QualifiedName
from libcst.metadata import QualifiedNameProvider
from libcst.metadata import QualifiedNameSource


class NoTypedDictRule(CstLintRule):
    """
    Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
    inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
    instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
    ``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_)
    """

    MESSAGE: str = "Instead of TypedDict, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency."
    METADATA_DEPENDENCIES = (QualifiedNameProvider,)

    VALID = [
        Valid(
            """
					@dataclass(frozen=True)
					class Foo:
						pass
					"""
        ),
        Valid(
            """
					@dataclass(frozen=False)
					class Foo:
						pass
					"""
        ),
        Valid(
            """
					class Foo:
						pass
					"""
        ),
        Valid(
            """
					class Foo(SomeOtherBase):
						pass
					"""
        ),
        Valid(
            """
					@some_other_decorator
					class Foo:
						pass
					"""
        ),
        Valid(
            """
					@some_other_decorator
					class Foo(SomeOtherBase):
						pass
					"""
        ),
    ]
    INVALID = [
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple):
                pass
            """,
            expected_replacement="""
            from typing import NamedTuple

            @dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple as NT

            class Foo(NT):
                pass
            """,
            expected_replacement="""
            from typing import NamedTuple as NT

            @dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            import typing as typ

            class Foo(typ.NamedTuple):
                pass
            """,
            expected_replacement="""
            import typing as typ

            @dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            class Foo(NamedTuple, AnotherBase, YetAnotherBase):
                pass
            """,
            expected_replacement="""
            from typing import NamedTuple

            @dataclass(frozen=True)
            class Foo(AnotherBase, YetAnotherBase):
                pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            class OuterClass(SomeBase):
                class InnerClass(NamedTuple):
                    pass
            """,
            expected_replacement="""
            from typing import NamedTuple

            class OuterClass(SomeBase):
                @dataclass(frozen=True)
                class InnerClass:
                    pass
            """,
        ),
        Invalid(
            code="""
            from typing import NamedTuple

            @some_other_decorator
            class Foo(NamedTuple):
                pass
            """,
            expected_replacement="""
            from typing import NamedTuple

            @some_other_decorator
            @dataclass(frozen=True)
            class Foo:
                pass
            """,
        ),
    ]

    qualified_typeddict = QualifiedName(name="typing_extensionsTypedDict", source=QualifiedNameSource.IMPORT)

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        (namedtuple_base, new_bases) = self.partition_bases(original_node.bases)
        if namedtuple_base is not None:
            call = ensure_type(parse_expression("dataclass(frozen=True)"), cst.Call)

            replacement = original_node.with_changes(
                lpar=MaybeSentinel.DEFAULT,
                rpar=MaybeSentinel.DEFAULT,
                bases=new_bases,
                decorators=list(original_node.decorators) + [cst.Decorator(decorator=call)],
            )
            self.report(original_node, replacement=replacement)

    def partition_bases(self, original_bases: Sequence[cst.Arg]) -> Tuple[Optional[cst.Arg], List[cst.Arg]]:
        # Returns a tuple of NamedTuple base object if it exists, and a list of non-NamedTuple bases
        namedtuple_base: Optional[cst.Arg] = None
        new_bases: List[cst.Arg] = []
        for base_class in original_bases:
            if QualifiedNameProvider.has_name(self, base_class.value, self.qualified_typeddict):
                namedtuple_base = base_class
            else:
                new_bases.append(base_class)
        return (namedtuple_base, new_bases)


__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if ((callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper()) and not str(getattr(v, "__name__", k)).startswith("__"))  # callables from this module  # or CONSTANTS
    ]
)  # neither marked internal

if __name__ == "__main__":
    print(__file__)
