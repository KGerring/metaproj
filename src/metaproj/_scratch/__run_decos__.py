#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = __run_decos__
# author=KGerring
# date = 7/8/21
# project poetryproj
# docs root 
"""
 poetryproj  ${FILE}

"""

from __future__ import annotations
import sys # isort:skip
import os # isort:skip
import re # isort:skip
from ast import literal_eval
from textwrap import dedent
from typing import Dict, List, Sequence, Set, Union

import libcst as cst
from libcst import matchers as m
from libcst.matchers import MatcherDecoratableTransformer, MatcherDecoratableVisitor, call_if_inside, call_if_not_inside, leave, visit


def fixture(code: str) -> cst.Module:
    return cst.parse_module(dedent(code))

def fixture0():
    "nested call"
    class TestVisitor_(MatcherDecoratableTransformer):
        def __init__(self) -> None:
            super().__init__()
            self.visits: List[str] = []

        @call_if_inside(m.ClassDef(m.Name("A")))
        @call_if_inside(m.FunctionDef(m.Name("foo")))
        def visit_SimpleString(self, node: cst.SimpleString) -> None:
            self.visits.append(node.value)

    module = fixture(
        """
		def foo() -> None:
			return "foo"

		class A:
			def foo(self) -> None:
				return "baz"
		"""
    )

    visitor = TestVisitor_()
    module.visit(visitor)

def test_simple():
    #: Set up a simple visitor with a visit and leave decorator.
    class _TestVisitor(MatcherDecoratableTransformer):  # line 709
        def __init__(self) -> None:
            super().__init__()
            self.visits: Set[str] = set()
            self.leaves: Set[str] = set()

        @call_if_inside(m.FunctionDef(m.Name("foo")))
        @visit(m.SimpleString())
        def visit_string1(self, node: cst.SimpleString) -> None:
            self.visits.add(literal_eval(node.value) + "1")

        @call_if_not_inside(m.FunctionDef(m.Name("bar")))
        @visit(m.SimpleString())
        def visit_string2(self, node: cst.SimpleString) -> None:
            self.visits.add(literal_eval(node.value) + "2")

        @call_if_inside(m.FunctionDef(m.Name("baz")))
        @leave(m.SimpleString())
        def leave_string1(
            self, original_node: cst.SimpleString, updated_node: cst.SimpleString
        ) -> cst.SimpleString:
            self.leaves.add(literal_eval(updated_node.value) + "1")
            return updated_node

        @call_if_not_inside(m.FunctionDef(m.Name("foo")))
        @leave(m.SimpleString())
        def leave_string2(
            self, original_node: cst.SimpleString, updated_node: cst.SimpleString
        ) -> cst.SimpleString:
            self.leaves.add(literal_eval(updated_node.value) + "2")
            return updated_node

    ########################################################
    # Parse a module and verify we visited correctly.
    def run():
        module = fixture(
            """
			a = "foo"
			b = "bar"
	
			def foo() -> None:
				return "baz"
	
			def bar() -> None:
				return "foobar"
	
			def baz() -> None:
				return "foobarbaz"
		"""
        )
        visitor = _TestVisitor()
        module.visit(visitor)

        # We should have only visited a select number of nodes.
        assert visitor.visits == {"baz1", "foo2", "bar2", "baz2", "foobarbaz2"}
        assert visitor.leaves == {"foobarbaz1", "foo2", "bar2", "foobar2", "foobarbaz2"}

def test_call_if_inside():
    # Set up a simple visitor with a call_if_inside decorator.
    class TestVisitor(MatcherDecoratableVisitor):  # 319
        def __init__(self) -> None:
            super().__init__()
            self.visits: List[str] = []
            self.leaves: List[str] = []

        @call_if_not_inside(m.FunctionDef(m.Name("foo")))
        def visit_SimpleString_lpar(self, node: cst.SimpleString) -> None:
            self.visits.append(node.value)

        @call_if_not_inside(m.FunctionDef())
        def leave_SimpleString_lpar(self, node: cst.SimpleString) -> None:
            self.leaves.append(node.value)

        # Parse a module and verify we visited correctly.

    module = fixture(
        """
				a = "foo"
				b = "bar"
		
				def foo() -> None:
					return "baz"
		
				def bar() -> None:
					return "foobar"
			"""
    )
    visitor = TestVisitor()
    module.visit(visitor)

    # We should have only visited a select number of nodes.
    self.assertEqual(visitor.visits, ['"foo"', '"bar"', '"foobar"'])
    self.assertEqual(visitor.leaves, ['"foo"', '"bar"'])

def test_comp():
    #: Set up a simple visitor with a visit and leave decorator.
    class TestCompVisitor(MatcherDecoratableTransformer):
        def __init__(self) -> None:
            super().__init__()
            self.visits: Set[str] = set()
            self.leaves: Set[str] = set()

        @call_if_inside(m.FunctionDef(m.Name("foo")))
        @visit(m.SimpleString())
        def visit_string1(self, node: cst.SimpleString) -> None:
            self.visits.add(literal_eval(node.value) + "1")

        @call_if_not_inside(m.FunctionDef(m.Name("bar")))
        @visit(m.SimpleString())
        def visit_string2(self, node: cst.SimpleString) -> None:
            self.visits.add(literal_eval(node.value) + "2")

        @call_if_inside(m.FunctionDef(m.Name("baz")))
        @leave(m.SimpleString())
        def leave_string1(
            self, original_node: cst.SimpleString, updated_node: cst.SimpleString
        ) -> cst.SimpleString:
            self.leaves.add(literal_eval(updated_node.value) + "1")
            return updated_node

        @call_if_not_inside(m.FunctionDef(m.Name("foo")))
        @leave(m.SimpleString())
        def leave_string2(
            self, original_node: cst.SimpleString, updated_node: cst.SimpleString
        ) -> cst.SimpleString:
            self.leaves.add(literal_eval(updated_node.value) + "2")
            return updated_node

    # Parse a module and verify we visited correctly.
    module = fixture(
        """
				a = "foo"
				b = "bar"
		
				def foo() -> None:
					return "baz"
		
				def bar() -> None:
					return "foobar"
		
				def baz() -> None:
					return "foobarbaz"
			"""
    )
    visitor = TestCompVisitor()
    module.visit(visitor)

    # We should have only visited a select number of nodes.
    assert visitor.visits == {"baz1", "foo2", "bar2", "baz2", "foobarbaz2"}
    assert visitor.leaves == {"foobarbaz1", "foo2", "bar2", "foobar2", "foobarbaz2"}

def test_param():
    # Set up a simple visitor with a call_if_inside decorator.
    class TestParamVisitor(MatcherDecoratableTransformer):
        def __init__(self) -> None:
            super().__init__()
            self.visits: List[str] = []

        @m.call_if_inside(
            m.FunctionDef(m.Name("foo"),
                          params=m.Parameters([m.ZeroOrMore()]))
        )
        def visit_SimpleString(self, node: cst.SimpleString) -> None:
            self.visits.append(node.value)

    # Parse a module and verify we visited correctly.
    def parse_it():
        module = fixture(
            """
				a = "foo"
				b = "bar"
		
				def foo() -> None:
					return "baz"
		
				def bar() -> None:
					return "foobar"
			"""
        )
        visitor = TestParamVisitor()
        module.visit(visitor)

        # We should have only visited a select number of nodes.
        assert visitor.visits == ['"baz"']

def _add_one(
    node: cst.CSTNode,
    extraction: Dict[str, Union[cst.CSTNode, Sequence[cst.CSTNode]]],
) -> cst.CSTNode:
    return cst.Integer(str(int(cst.ensure_type(node, cst.Integer).value) + 1))

def test_replace_add_one() -> None:
    original = cst.parse_module("foo: int = 36\ndef bar() -> int:\n    return 41\n")
    replaced = m.replace(original, m.Integer(), _add_one)
    assert replaced == "foo: int = 37\ndef bar() -> int:\n    return 42\n"

def test_replace_add_one_to_foo_args() -> None:
    def _add_one_to_arg(
        node: cst.CSTNode,
        extraction: Dict[str, Union[cst.CSTNode, Sequence[cst.CSTNode]]],
    ) -> cst.CSTNode:
        return node.deep_replace(
            # This can be either a node or a sequence, pyre doesn't know.
            cst.ensure_type(extraction["arg"], cst.CSTNode),
            # Grab the arg and add one to its value.
            cst.Integer(
                str(int(cst.ensure_type(extraction["arg"], cst.Integer).value) + 1)
            ),
        )

    # Verify way more complex transform behavior.
    original = cst.parse_module(
        "foo: int = 37\ndef bar(baz: int) -> int:\n    return baz\n\nbiz: int = bar(41)\n"
    )
    replaced = cst.ensure_type(
        m.replace(
            original,
            m.Call(
                func=m.Name("bar"),
                args=[m.Arg(m.SaveMatchedNode(m.Integer(), "arg"))],
            ),
            _add_one_to_arg,
        ),
        cst.Module,
    ).code

    assert (
        replaced
        == "foo: int = 37\ndef bar(baz: int) -> int:\n    return baz\n\nbiz: int = bar(42)\n"
    )