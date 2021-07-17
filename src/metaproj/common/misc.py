#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = misc
# author=KGerring
# date = 6/12/21
# project poetryproj
# docs root
"""
 poetryproj  

"""
from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path
from typing import (
    Generator,
    List,
    Literal,
    Tuple,
    Type,
    Union,
)

import click
import libcst as cst
from attr import field
from libcst._nodes.base import CSTNode
from libcst._nodes.module import Module
from libcst._parser.detect_config import detect_config
from libcst._parser.grammar import get_grammar, validate_grammar
from libcst._parser.python_parser import PythonCSTParser
from libcst._parser.types.config import PartialParserConfig
from libcst.codemod import (
    CodemodContext,
    ContextAwareTransformer,
    VisitorBasedCodemodCommand,
    parallel_exec_transform_with_prettyprint,
)

from .path_utils import get_sources


def make_lenient_parser():
    from libcst._exceptions import EOFSentinel, ParserSyntaxError, get_expected_str
    from libcst._parser.python_parser import PythonCSTParser
    from libcst._parser.base_parser import (
        StackNode,
        _token_to_transition,
        _TokenT,
    )
    class ParseTokenError(Exception):
        def __init__(self, msg: str, token: str, token_idx: int):
            super().__init__("Failed parsing token: " + msg)
            self.token = token
            self.token_idx = token_idx
    
        def get_erroneous_token(self) -> Tuple[str, int]:
            return self.token, self.token_idx
        
    class LenientPythonParser(PythonCSTParser):
        def __init__(self, *args, **kwargs):
            super(LenientPythonParser, self).__init__(*args, **kwargs)
    
        def _add_token(self, token: _TokenT) -> None:
            grammar = self._pgen_grammar
            stack = self.stack
            # _token_to_transition
            # _token_to_transition
            transition = _token_to_transition(grammar, token.type, token.string)
    
            while True:
                try:
                    plan = stack[-1].dfa.transitions[transition]
                    break
                except KeyError:
                    if stack[-1].dfa.is_final:
                        self._pop()
                    else:
                        expected_str = get_expected_str(
                            token, stack[-1].dfa.transitions.keys()
                        )
                        raise ParseTokenError(expected_str, token, token.start_pos[1])
    
            stack[-1].dfa = plan.next_dfa
    
            for push in plan.dfa_pushes:
                stack.append(StackNode(push))
    
            leaf = self.convert_terminal(token)
            stack[-1].nodes.append(leaf)
    
        def parse(self):
            for token in self.tokens:
                self._add_token(token)
    
            while True:
                tos = self.stack[-1]
                if not tos.dfa.is_final:
                    expected_str = get_expected_str(
                        EOFSentinel.EOF, tos.dfa.transitions.keys()
                    )
                    raise ParserSyntaxError(
                        f"{expected_str}",
                        lines=self.lines,
                        raw_line=len(self.lines),
                        raw_column=len(self.lines[-1]),
                    )
    
                if len(self.stack) > 1:
                    self._pop()
                else:
                    return self.convert_nonterminal(tos.nonterminal, tos.nodes)
    
    def _lenient_parse(
        entrypoint: str,
        source: Union[str, bytes],
        config: PartialParserConfig,
        *,
        detect_trailing_newline: bool,
        detect_default_newline: bool,
    ) -> CSTNode:
        detection_result = detect_config(
            source,
            partial=config,
            detect_trailing_newline=detect_trailing_newline,
            detect_default_newline=detect_default_newline,
        )
        validate_grammar()
        grammar = get_grammar(config.parsed_python_version, config.future_imports)
        parser = LenientPythonParser(
            tokens=detection_result.tokens,
            config=detection_result.config,
            pgen_grammar=grammar,
            start_nonterminal=entrypoint,
        )
    
        result = parser.parse()
        assert isinstance(result, CSTNode)
        return result
    
    def lenient_parse_module(
        source: Union[str, bytes],
        config: PartialParserConfig = PartialParserConfig(),
    ) -> Module:
    
        try:
            result = _lenient_parse(
                "file_input",
                source,
                config,
                detect_trailing_newline=True,
                detect_default_newline=True,
            )
            assert isinstance(result, Module)
            return result
        except ParseTokenError as pse:
            token, idx = pse.get_erroneous_token()
            return lenient_parse_module(source[:idx] + "" + source[idx + 1 :], config)
    
_DEFAULT_PARTIAL_PARSER_CONFIG: PartialParserConfig = PartialParserConfig()

ENTRYPOINTS = Literal["file_input", "stmt_input", "expression_input"]

StackNode: libcst._parser.base_parser.StackNode
BaseParser: libcst._parser.base_parser.BaseParser
NFAState: libcst._parser.parso.pgen2.grammar_parser.NFAState
GrammarParser: libcst._parser.parso.pgen2.grammar_parser.GrammarParser
NFAArc: libcst._parser.parso.pgen2.grammar_parser.NFAArc
DFAPlan: libcst._parser.parso.pgen2.generator.DFAPlan
DFAState: libcst._parser.parso.pgen2.generator.DFAState
ReservedString: libcst._parser.parso.pgen2.generator.ReservedString
Grammar: libcst._parser.parso.pgen2.generator.Grammar
PythonTokenTypes: libcst._parser.parso.python.token.PythonTokenTypes


# @dataclass
def EntryParserHolder():
    """stmt_input this is False stmt_input
    _make_transition(token_namespace,
            reserved_syntax_strings: ReservedString,
            label)


            "stmt_input":
                    detect_trailing_newline=True,
                    detect_default_newline=False,
                    ret = Union[SimpleStatementLine, BaseCompoundStatement]

    "expression_input":
            detect_trailing_newline=False,
            detect_default_newline=False,
            ret = BaseExpression
    """
    pass

    entrypoint: ENTRYPOINTS = "file_input"
    config: PartialParserConfig
    detect_trailing_newline: bool = field(default=True)
    detect_default_newlinee: bool = field(default=True)  # detect_default_newline
    retvar: libcst.CSTNode = field(default=Module)

    detection_result: libcst._parser.detect_config.ConfigDetectionResult = (
        None  # detect_config(  source,
    )
    from libcst._parser.detect_config import detect_config

    # _DEFAULT_PARTIAL_PARSER_CONFIG

    version: Any = ""

    source: str = "import os"
    _config: _DEFAULT_PARTIAL_PARSER_CONFIG
    grammar: generator.Grammar
    detect_trailing_newline = True
    detect_default_newline = True

    detection_result = detect_config(
        source,
        partial=_config,
        detect_trailing_newline=detect_trailing_newline,
        detect_default_newline=detect_default_newline,
    )
    grammar = None  # _pgen_grammar; validate_grammar()
    # grammar = get_grammar(config.parsed_python_version, config.future_imports)
    grammar = get_grammar(
        config.parsed_python_version, config.future_imports
    )  # Grammar[TokenType]

    parser: PythonCSTParser = field(default=None, init=False)
    result = None  # retvar
    extra = dict()  # _pgen_grammar
    to_dfa = None
    # libcst._parser.types.config.ParserConfig

    # nonterminal_to_dfas
    # tos = self.stack[-1]
    # expected_str = get_expected_str(EOFSentinel.EOF, tos.dfa.transitions.keys())
    # convert_nonterminal(tos.nonterminal, tos.nodes)
    # tos.dfa.transitions.keys()     #config
    # convert_nonterminal(tos.nonterminal, tos.nodes)

def parse(
        source: Union[str, bytes],
        entrypoint,
        config: PartialParserConfig, **kwargs
):
    detect_trailing_newline = True
    detect_default_newline = True


def _parse(
    entrypoint: str,
    source: Union[str, bytes],
    config: PartialParserConfig,
    *,
    detect_trailing_newline: bool,
    detect_default_newline: bool,
) -> CSTNode:

    detection_result = detect_config(
        source,
        partial=config,
        detect_trailing_newline=detect_trailing_newline,
        detect_default_newline=detect_default_newline,
    )

    # from libcst._parser.grammar import get_grammar, validate_grammar, PythonVersionInfo, parse_version_string, generate_grammar, Grammar
    validate_grammar()
    # libcst._parser.parso.pgen2.generator.generate_grammar(bnf_string, token_namespac: PythonTokenTypes)

    grammar = get_grammar(
        config.parsed_python_version, config.future_imports
    )  # Grammar[TokenType]
    """
	Grammar[TokenType]
		grammar.nonterminal_to_dfas, reserved_syntax_strings, start_nonterminal
		
		
	parser:
		for token in self.tokens:
			self._add_token(token)
			
		
		while True:
			tos = self.stack[-1]        #: libcst._parser.base_parser.StackNode
			if not tos.dfa.is_final:
				pass
				
			if len(self.stack) > 1:
				self._pop()
			else:                              tos.dfa.from_rule
				return self.convert_nonterminal(tos.nonterminal = 'file_input', tos.nodes)
				
				parser.nonterminal_conversions['file_input'](self.config, children = tos.nodes) -> Module
		
	_add_token(token)
		grammar = self._pgen_grammar
		stack = self.stack
		transition = libcst._parser.base_parser._token_to_transition(grammar, token.type, token.string)
		while True:
			try:
				plan = stack[-1].dfa.transitions[transition]
				break
			except KeyError:
				if stack[-1].dfa.is_final:
					try:
						self._pop()
			else:
			EOF Error
		
		stack[-1].dfa = plan.next_dfa
		for push in plan.dfa_pushes:
			stack.append(StackNode(push))
		leaf = self.convert_terminal(token)
		stack[-1].nodes.append(leaf)
	
	"""
    parser = PythonCSTParser(
        tokens=detection_result.tokens,
        config=detection_result.config,
        pgen_grammar=grammar,
        start_nonterminal=entrypoint,
    )
    # The parser has an Any return type, we can at least refine it to CSTNode here.
    result = parser.parse()


class BaseCodemodCommand(
        VisitorBasedCodemodCommand, ABC
):
    """Base class for our commands."""

    transformers: List[Type[ContextAwareTransformer]]

    def __init__(self, transformers, context: CodemodContext) -> None:
        self.transformers = transformers
        super().__init__(context)

    def transform_module_impl(self, tree: cst.Module) -> cst.Module:
        for transform in self.transformers:
            inst = transform(self.context)
            tree = inst.transform_module(tree)
        return tree


def iter_codemodders(visitors) -> Generator[Type[CodemodTransformer], None, None]:
    """Iterator of all the codemodders classes."""
    for object_name in dir(visitors):
        try:
            obj = getattr(visitors, object_name)
            if issubclass(obj, BaseCodemodCommand) and not inspect.isabstract(obj):
                yield obj  # Looks like this one is good to go
        except TypeError:
            continue

BY_NAME = {cls.__name__: cls for cls in iter_codemodders(None)}

class CodemodChoice(click.Choice):
    def get_metavar(self, param):
        return "(see `codemod list`)"

@click.group()
def codemod():
    """Automatically fix."""

@codemod.command()
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=True, readable=True, allow_dash=True
    ),
    required=True,
)
@click.option(
    "--codemod",
    "codemod",
    help="Choose a specific codemod to run. Can be repeated.",
    type=CodemodChoice(BY_NAME.keys()),
    multiple=True,
)
def run(
    codemod: List[str],
    src: Tuple[str, ...],
) -> None:
    """
    Automatically fixes deprecations removed Django deprecations.
    This command takes the path to target as argument and a version of
    Django to select code modifications to apply.
    """
    codemodders_set = set()
    for name in codemod:
        codemodders_set.add(BY_NAME[name])
    if not codemodders_set:
        raise click.UsageError(
            "No codemods were selected. "
            "Specify '--removed-in' and/or '--deprecated-in' and/or '--codemod'."
        )
    codemodders_list = sorted(codemodders_set, key=lambda m: m.__name__)
    click.echo(f"Running codemods: {', '.join(m.__name__ for m in codemodders_list)}")
    command_instance = BaseCodemodCommand(codemodders_list, CodemodContext())
    files = get_sources(src)
    call_command(command_instance, files)


def call_command(
    command_instance: BaseCodemodCommand,
    files: List[Path],
):
    """Call libCST with our customized command."""
    try:
        # Super simplified call
        result = parallel_exec_transform_with_prettyprint(
            command_instance,
            files,  # type: ignore
        )
    except KeyboardInterrupt:
        raise click.Abort("Interrupted!")

    # fancy summary a-la libCST
    total = result.successes + result.skips + result.failures
    click.echo(f"Finished codemodding {total} files!")
    click.echo(f" - Transformed {result.successes} files successfully.")
    click.echo(f" - Skipped {result.skips} files.")
    click.echo(f" - Failed to codemod {result.failures} files.")
    click.echo(f" - {result.warnings} warnings were generated.")
    if result.failures > 0:
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    print(__file__)
