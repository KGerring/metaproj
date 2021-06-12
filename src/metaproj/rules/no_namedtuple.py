#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from __future__ import annotations # isort:skip
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import libcst as cst
from fixit import CstLintRule
from fixit import InvalidTestCase as Invalid
from fixit import ValidTestCase as Valid
from libcst import MaybeSentinel
from libcst import ensure_type
from libcst import parse_expression
from libcst.codemod import VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.codemod.visitors import RemoveImportsVisitor
from libcst.metadata import ProviderT
from libcst.metadata import QualifiedName
from libcst.metadata import QualifiedNameProvider
from libcst.metadata import QualifiedNameSource


class NoNamedTupleRule(CstLintRule):
    """
    Enforce the use of ``dataclasses.dataclass`` decorator instead of ``NamedTuple`` for cleaner customization and
    inheritance. It supports default value, combining fields for inheritance, and omitting optional fields at
    instantiation. See `PEP 557 <https://www.python.org/dev/peps/pep-0557>`_.
    ``@dataclass`` is faster at reading an object's nested properties and executing its methods. (`benchmark <https://medium.com/@jacktator/dataclass-vs-namedtuple-vs-object-for-performance-optimization-in-python-691e234253b9>`_)
    """

    MESSAGE: str = "Instead of NamedTuple, consider using the @dataclass decorator from dataclasses instead for simplicity, efficiency and consistency."
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

    qualified_namedtuple = QualifiedName(name="typing.NamedTuple", source=QualifiedNameSource.IMPORT)

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
            if QualifiedNameProvider.has_name(self, base_class.value, self.qualified_namedtuple):
                namedtuple_base = base_class
            else:
                new_bases.append(base_class)
        return (namedtuple_base, new_bases)


######


class ConvertNamedTupleToDataclassCommand(VisitorBasedCodemodCommand):
    """
    Convert NamedTuple class declarations to Python 3.7 dataclasses.

    This only performs a conversion at the class declaration level.
    It does not perform type annotation conversions, nor does it convert
    NamedTuple-specific attributes and methods.
    """

    DESCRIPTION: str = "Convert NamedTuple class declarations to Python 3.7 dataclasses using the @dataclass decorator."
    METADATA_DEPENDENCIES: Sequence[ProviderT] = (QualifiedNameProvider,)

    # The 'NamedTuple' we are interested in
    qualified_namedtuple: QualifiedName = QualifiedName(name="typing.NamedTuple", source=QualifiedNameSource.IMPORT)
    qualified_dataclass: QualifiedName = QualifiedName(name="dataclasses.dataclass", source=QualifiedNameSource.IMPORT)
    attr_dataclass: QualifiedName = QualifiedName(name="attr.dataclass", source=QualifiedNameSource.IMPORT)

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        new_bases: List[cst.Arg] = []
        namedtuple_base: Optional[cst.Arg] = None

        # Need to examine the original node's bases since they are directly tied to import metadata
        for base_class in original_node.bases:
            # Compare the base class's qualified name against the expected typing.NamedTuple
            if not QualifiedNameProvider.has_name(self, base_class.value, self.qualified_namedtuple):
                # Keep all bases that are not of type typing.NamedTuple
                new_bases.append(base_class)
            else:
                namedtuple_base = base_class

        # We still want to return the updated node in case some of its children have been modified
        if namedtuple_base is None:
            return updated_node

        AddImportsVisitor.add_needed_import(self.context, "attr", "dataclass")
        AddImportsVisitor.add_needed_import(self.context, "pydantic.dataclasses", "dataclass")
        RemoveImportsVisitor.remove_unused_import_by_node(self.context, namedtuple_base.value)

        call = cst.ensure_type(
            cst.parse_expression("dataclass(frozen=False)", config=self.module.config_for_parsing),
            cst.Call,
        )
        return updated_node.with_changes(
            lpar=cst.MaybeSentinel.DEFAULT,
            rpar=cst.MaybeSentinel.DEFAULT,
            bases=new_bases,
            decorators=[*original_node.decorators, cst.Decorator(decorator=call)],
        )
