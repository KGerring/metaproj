"""

taken from `https://github.com/tsoernes/print_to_logging_libcst` repo for ideas

"""
import argparse
import importlib
import inspect
import re
import sys
from difflib import context_diff, unified_diff
from pathlib import Path
from shutil import get_terminal_size
from typing import List, Optional, Union

import libcst as cst
import libcst.matchers as m
from libcst import (Arg, Attribute, Call, ClassDef, Comment,
                    ConcatenatedString, CSTNodeT, Expr, FormattedString,
                    FormattedStringExpression, FunctionDef, Module, Name,
                    RemovalSentinel, SimpleStatementLine, SimpleString)

from libcst.metadata import (ParentNodeProvider,
                             PositionProvider,
                             WhitespaceInclusivePositionProvider)
from libcst.codemod import ContextAwareTransformer, CodemodContext

levels = {
    'i': 'info',
    'w': 'warning',
    'e': 'error',
    'c': 'critical',
    'x': 'exception',
}

class Bcolor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

class RemoveCommentsTransformer(cst.CSTTransformer):
    # def leave_EmptyLine(
    #     self, original_node: cst.EmptyLine, updated_node: cst.EmptyLine
    # ) -> cst.EmptyLine:
    #     if updated_node.comment is not None:
    #         return updated_node.with_changes(comment=None)
    #     return updated_node

    def leave_TrailingWhitespace(
        self, original_node: cst.TrailingWhitespace, updated_node: cst.TrailingWhitespace
    ) -> cst.TrailingWhitespace:

        if updated_node.comment is not None:
            return updated_node.with_changes(comment=None)
        return updated_node

class GatherCommentsVisitor(cst.CSTVisitor):
    def __init__(self) -> None:
        self.comments = []

    def get_joined_comment(self, sep) -> Optional[Comment]:
        comment = sep.join([re.sub(r'# *', '', c) for c in self.comments])
        comment = Comment(value='# ' + comment) if comment else None
        return comment

    # def visit_EmptyLine(self, node: cst.EmptyLine) -> bool:
    #     if node.comment is not None:
    #         self.handle_comment(node)
    #     return False

    def visit_TrailingWhitespace(self, node: cst.TrailingWhitespace) -> bool:
        if node.comment is not None:
            self.handle_comment(node)
        return False

    def handle_comment(self, node: Union[cst.EmptyLine, cst.TrailingWhitespace]) -> None:
        comment = node.comment
        assert comment is not None  # ensured by callsites above
        self.comments.append(comment.value)

class GatherStringVisitor(cst.CSTVisitor):
    def __init__(self) -> None:
        self.strings = []

    def on_visit(self, node: cst.EmptyLine) -> bool:
        if isinstance(node, SimpleString):
            self.strings.append(node.value)
        return True

def get_keyword(node: cst.Call, kw, default=None) -> bool:
    for arg in node.args:
        if m.matches(arg.keyword, m.Name(kw)):
            return arg.value.value
    return default

def extract_string(string: str) -> str:
    """
    Remove quotes and leading r/f from string
    """
    string = re.sub('^[rfRF]+', '', string)
    if not (string.startswith('"') or string.startswith("'")):
        raise TypeError('not an inner string')
    n_quotes = len(re.match(r'^("""|\'\'\'|"|\')', string).group(1))
    string = string[n_quotes:-n_quotes]
    return string

def make_str(string: FormattedString) -> str:
    code = cst.parse_module("").code_for_node(string)
    inner = re.match(string.start + '(.*)' + string.end + '$', code).group(1)
    return inner


class LoggerTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (
            WhitespaceInclusivePositionProvider, PositionProvider, ParentNodeProvider
    )
    
    def __init__(
            self,
            fpath,
            lines,
            default_level='info',
            accept_all=False,
            comment_sep=' / ',
            context_lines=13,
    ):
        self.fpath = fpath
        self.lines = lines
        self.default_level: str = default_level
        self.accept_all: bool = accept_all
        self.comment_sep: str = comment_sep
        self.context_lines: int = context_lines
    
    def get_parent(self, node) -> CSTNodeT:
        return self.get_metadata(cst.metadata.ParentNodeProvider, node)
    
    def handle_string(self,
                      original_node: SimpleStatementLine,
                      updated_node: SimpleStatementLine):pass
    
    def on_leave(self,
                 original_node: CSTNodeT,
                 updated_node: CSTNodeT) -> Union[CSTNodeT, RemovalSentinel]:
        # Visit line nodes with print function calls
        if not isinstance(updated_node, SimpleStatementLine):
            return updated_node
        
        original_line_node = original_node
        line_node = updated_node
        
        if not isinstance(line_node.body[0], Expr):
            return updated_node
        
        node = line_node.body[0].value
        original_node = original_node.body[0].value
        
        if not (isinstance(node, Call) and node.func.value == 'print'):
            return line_node
        
        pos_args = [x.value for x in node.args if not x.keyword]
        
        has_vars = False
        terms = []
        n_variables = 0
        simple_ixs = []  # indexes of regular, simple strings
        for ix, arg in enumerate(pos_args):
            if isinstance(arg, FormattedString):
                for part in arg.parts:
                    if isinstance(part, FormattedStringExpression):
                        has_vars = True
                        break
                term = make_str(arg)
                terms.append(term)
                
            elif isinstance(arg, SimpleString):
                term = extract_string(arg.value)
                terms.append(term)
                simple_ixs.append(ix)
                
            elif isinstance(arg, ConcatenatedString):
                visitor = GatherStringVisitor()
                arg.visit(visitor)
                term = ''.join([extract_string(s) for s in visitor.strings])
                terms.append(term)
                simple_ixs.append(ix)
            
            elif isinstance(arg, Name):
                has_vars = True
                n_variables += 1
                terms.append('{' + arg.value + '}')
        
        # Escape {} in non-f strings
        if has_vars:
            for ix in simple_ixs:
                term = terms[ix]
                terms[ix] = term.replace('{', '{{').replace('}', '}}')
        
        sep = ' '
        sep_ = get_keyword(node, 'sep')
        try:
            # fails if sep is a variable
            sep = extract_string(sep_)
        except TypeError:
            pass
        
        if n_variables == len(terms) == 1:
            # Avoid putting a single variable inside f-string
            arg_line = terms[0]
        else:
            arg_line = '"' + sep.join(terms) + '"'
            if has_vars:
                arg_line = 'f' + arg_line
        
        args = [Arg(value=cst.parse_expression(arg_line))]
        
        # Gather up comments
        cst.metadata.MetadataWrapper(original_line_node)
        cg = GatherCommentsVisitor()
        original_line_node.visit(cg)
        comment = cg.get_joined_comment(self.comment_sep)
        
        # Remove all comments in order to put them all at the end
        rc_trans = RemoveCommentsTransformer()
        line_node = line_node.visit(rc_trans)
        
        def get_line_node(level):
            func = Attribute(value=Name('logging'), attr=Name(level))
            node_ = node.with_changes(func=func, args=args)
            
            line_node_ = line_node.deep_replace(line_node.body[0].value, node_)
            line_node_ = line_node_.with_deep_changes(
                    line_node_.trailing_whitespace, comment=comment
            )
            return line_node_
        
        line_node = get_line_node(self.default_level)
        
        # pos = self.get_metadata(WhitespaceInclusivePositionProvider, original_line_node)
        pos = self.get_metadata(PositionProvider, original_line_node)
        lineix = pos.start.line - 1  # 1 indexed line number
        end_lineix, end_lineno = pos.end.line - 1, pos.end.line
        
        # Predict the source code for the newly changed line node
        module_node = original_line_node
        while not isinstance(module_node, Module):
            module_node = self.get_parent(module_node)
        
        # n_lines = len(cst.parse_module("").code_for_node(line_node).splitlines())
        # new_code = module_node.deep_replace(original_line_node, line_node).code
        # line = '\n'.join(new_code.splitlines()[lineix:lineix + n_lines])
        line = cst.parse_module("").code_for_node(line_node)
        
        # Find the function or class containing the print line
        context_node = original_line_node
        while not isinstance(context_node, (FunctionDef, ClassDef, Module)):
            context_node = self.get_parent(context_node)
        if isinstance(context_node, Module):
            source_context = ''
        else:
            source_context = '/' + context_node.name.value
        
        print(
                Bcolor.HEADER, f"{self.fpath}{source_context}:"
                               f"{lineix + 1}-{end_lineix + 1}", Bcolor.ENDC
        )
        print()
        print_context2(self.lines, lineix, end_lineno, line, self.context_lines)
        print()
        
        import ipdb
        
        # ipdb.set_trace()
        # Query the user to decide whether to accept, modify, or reject changes
        if self.accept_all:
            return line_node
        inp = None
        while inp not in ['', 'y', 'n', 'A', 'i', 'w', 'e', 'c', 'x', 'q']:
            inp = input(
                    Bcolor.OKCYAN + "Accept change? ("
                                    f"y = yes ({self.default_level}) [default], "
                                    "n = no, "
                                    "A = yes to all, "
                                    "i = yes (info), "
                                    "w = yes (warning), "
                                    "e = yes (error), "
                                    "c = yes (critical), "
                                    "x = yes (exception), "
                                    "q = quit): " + Bcolor.ENDC
            )
        if inp in ('q', 'Q'):
            sys.exit(0)
        elif inp == 'n':
            return original_line_node
        elif inp in ['i', 'w', 'e', 'c', 'x']:
            level = levels[inp]
            line_node = get_line_node(level)
        elif inp == 'A':
            self.accept_all = True
        
        return line_node




class Transformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (
        WhitespaceInclusivePositionProvider, PositionProvider, ParentNodeProvider
    )

    def __init__(
        self,
        fpath,
        lines,
        default_level='info',
        accept_all=False,
        comment_sep=' / ',
        context_lines=13,
    ):
        self.fpath = fpath
        self.lines = lines
        self.default_level: str = default_level
        self.accept_all: bool = accept_all
        self.comment_sep: str = comment_sep
        self.context_lines: int = context_lines

    def get_parent(self, node) -> CSTNodeT:
        return self.get_metadata(cst.metadata.ParentNodeProvider, node)

    def on_leave(self,
                 original_node: CSTNodeT,
                 updated_node: CSTNodeT) -> Union[CSTNodeT, RemovalSentinel]:
        # Visit line nodes with print function calls
        if not isinstance(updated_node, SimpleStatementLine):
            return updated_node
        
        original_line_node = original_node
        
        line_node = updated_node

        if not isinstance(line_node.body[0], Expr):
            return updated_node
        
        node = line_node.body[0].value
        original_node = original_node.body[0].value
        
        if not (isinstance(node, Call) and node.func.value == 'print'):
            return line_node

        pos_args = [x.value for x in node.args if not x.keyword]

        has_vars = False
        terms = []
        n_variables = 0
        simple_ixs = []  # indexes of regular, simple strings
        for ix, arg in enumerate(pos_args):
            if isinstance(arg, FormattedString):
                for part in arg.parts:
                    if isinstance(part, FormattedStringExpression):
                        has_vars = True
                        break
                term = make_str(arg)
                terms.append(term)
                
            elif isinstance(arg, SimpleString):
                term = extract_string(arg.value)
                terms.append(term)
                simple_ixs.append(ix)
            elif isinstance(arg, ConcatenatedString):
                visitor = GatherStringVisitor()
                arg.visit(visitor)
                term = ''.join([extract_string(s) for s in visitor.strings])
                terms.append(term)
                simple_ixs.append(ix)

            elif isinstance(arg, Name):
                has_vars = True
                n_variables += 1
                terms.append('{' + arg.value + '}')

        # Escape {} in non-f strings
        if has_vars:
            for ix in simple_ixs:
                term = terms[ix]
                terms[ix] = term.replace('{', '{{').replace('}', '}}')

        sep = ' '
        sep_ = get_keyword(node, 'sep')
        try:
            # fails if sep is a variable
            sep = extract_string(sep_)
        except TypeError:
            pass

        if n_variables == len(terms) == 1:
            # Avoid putting a single variable inside f-string
            arg_line = terms[0]
        else:
            arg_line = '"' + sep.join(terms) + '"'
            if has_vars:
                arg_line = 'f' + arg_line

        args = [Arg(value=cst.parse_expression(arg_line))]

        # Gather up comments
        cst.metadata.MetadataWrapper(original_line_node)
        cg = GatherCommentsVisitor()
        original_line_node.visit(cg)
        comment = cg.get_joined_comment(self.comment_sep)

        # Remove all comments in order to put them all at the end
        rc_trans = RemoveCommentsTransformer()
        line_node = line_node.visit(rc_trans)

        def get_line_node(level):
            func = Attribute(value=Name('logging'), attr=Name(level))
            
            node_ = node.with_changes(func=func, args=args)
            
            line_node_ = line_node.deep_replace(line_node.body[0].value, node_)
            
            line_node_ = line_node_.with_deep_changes(
                line_node_.trailing_whitespace, comment=comment
            )
            return line_node_

        line_node = get_line_node(self.default_level)

        # pos = self.get_metadata(WhitespaceInclusivePositionProvider, original_line_node)
        pos = self.get_metadata(PositionProvider, original_line_node)
        lineix = pos.start.line - 1  # 1 indexed line number
        end_lineix, end_lineno = pos.end.line - 1, pos.end.line

        # Predict the source code for the newly changed line node
        module_node = original_line_node
        while not isinstance(module_node, Module):
            module_node = self.get_parent(module_node)

        # n_lines = len(cst.parse_module("").code_for_node(line_node).splitlines())
        # new_code = module_node.deep_replace(original_line_node, line_node).code
        # line = '\n'.join(new_code.splitlines()[lineix:lineix + n_lines])
        line = cst.parse_module("").code_for_node(line_node)

        # Find the function or class containing the print line
        context_node = original_line_node
        while not isinstance(context_node, (FunctionDef, ClassDef, Module)):
            context_node = self.get_parent(context_node)
            
        if isinstance(context_node, Module):
            source_context = ''
        else:
            source_context = '/' + context_node.name.value

        print(
            Bcolor.HEADER, f"{self.fpath}{source_context}:"
            f"{lineix+1}-{end_lineix+1}", Bcolor.ENDC
        )
        print()
        print_context2(self.lines, lineix, end_lineno, line, self.context_lines)
        print()

        import ipdb

        # ipdb.set_trace()
        # Query the user to decide whether to accept, modify, or reject changes
        if self.accept_all:
            return line_node
        inp = None
        while inp not in ['', 'y', 'n', 'A', 'i', 'w', 'e', 'c', 'x', 'q']:
            inp = input(
                Bcolor.OKCYAN + "Accept change? ("
                f"y = yes ({self.default_level}) [default], "
                "n = no, "
                "A = yes to all, "
                "i = yes (info), "
                "w = yes (warning), "
                "e = yes (error), "
                "c = yes (critical), "
                "x = yes (exception), "
                "q = quit): " + Bcolor.ENDC
            )
        if inp in ('q', 'Q'):
            sys.exit(0)
        elif inp == 'n':
            return original_line_node
        elif inp in ['i', 'w', 'e', 'c', 'x']:
            level = levels[inp]
            line_node = get_line_node(level)
        elif inp == 'A':
            self.accept_all = True

        return line_node



def clear_terminal():
    print("\n" * get_terminal_size().lines, end='')

def print_context2(
    lines: List[str], lineix: int, end_lineno: int, new_line: int, context_lines: int = 13
) -> None:
    new_lines = lines.copy()
    for ix in reversed(range(lineix, end_lineno)):
        del new_lines[ix]
    for line in reversed(new_line.splitlines()):
        new_lines.insert(lineix, line)
    print('\n'.join(context_diff(lines, new_lines, n=context_lines)))


def print_context(
    lines: List[str], lineix: int, end_lineno: int, new_line: int, context_lines: int = 13
) -> None:
    """
    Print the source code diff, with `context_lines` number of lines before and after
    the modified part
    """
    lines = lines.copy()
    new_lines = new_line.splitlines()
    for i, l in enumerate(new_lines):
        lines.insert(end_lineno + 1, l)
    lines = [' ' + ll for ll in lines]
    lines[end_lineno] = Bcolor.OKGREEN + '+' + lines[end_lineno][1:] + Bcolor.ENDC
    for lno in range(lineix, end_lineno):
        lines[lno] = Bcolor.FAIL + '-' + lines[lno][1:] + Bcolor.ENDC
    lines = lines[max(0, lineix - context_lines):end_lineno - 1 + context_lines]
    print('\n'.join(lines))


def modify(
    dir_: Path,
    paths: List[Path],
    default_level: str = 'info',
    accept_all: bool = False,
    context_lines: int = 13,
    comment_sep: str = ' // ',
    **_kwargs,
) -> None:
    for path in paths:
        fpath: str = str(path.relative_to(dir_))
        text: str = path.read_text()
        lines: list = text.splitlines()

        source_tree = cst.parse_module(text)
        transformer = Transformer(
            fpath, lines, default_level, accept_all, comment_sep, context_lines
        )
        wrapper = cst.metadata.MetadataWrapper(source_tree)
        modified_tree = wrapper.visit(transformer)
        if source_tree != modified_tree:
            path.write_text(modified_tree.code)


def confirm_action(desc='Really execute?') -> bool:
    """
    Return True if user confirms with 'Y' input
    """
    inp = ''
    while inp.lower() not in ['y', 'n']:
        inp = input(desc + ' Y/N: ')
    return inp == 'y'


def get_module_files(module: str) -> List[Path]:
    """
    Find all .py files in the directory of an importable module
    """
    mod = importlib.import_module(module)
    moddir = Path(inspect.getsourcefile(mod)).parent
    paths = get_paths(moddir)
    return moddir, paths


def get_paths(dir_: Path) -> List[Path]:
    return [x.resolve() for x in dir_.glob('**/*.py')]


parser = argparse.ArgumentParser(
        description='Refactoring tool to replace print with logging',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

def _get_parser():
    parser = argparse.ArgumentParser(
        description='Refactoring tool to replace print with logging',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', type=Path)
    group.add_argument(
        '-d',
        '--directory',
        type=Path,
        help='Find all .py paths in the directory and its subdirectories',
    )
    group.add_argument(
        '-m',
        '--module',
        type=str,
        help='Find all .py paths in the directory of the module and its subdirectories',
    )

    parser.add_argument(
        '-l',
        '--level',
        default='info',
        dest='default_level',
        choices=list(levels.values()),
        help="Default logging level",
    )
    parser.add_argument(
        '--accept_all',
        default=False,
        action='store_true',
        help="Auto accept all changes",
    )
    # parser.add_argument(
    #     '--no_single_var_fstrings',
    #     default=False,
    #     action='store_true',
    #     help="Do not convert \"print(x)\" into \"logging.info(f'{x}')\"",
    # )
    parser.add_argument(
        '--context_lines',
        default=13,
        type=int,
        help="Number of lines before and after change in diff"
    )
    parser.add_argument(
        '--comment_sep',
        default=' // ',
        type=str,
        help="Separator to use when joining multiline comments"
    )
    return parser

######
#utils, bandit.core.test_set, bandit.core.manager, bandit.core.context, bandit.core.config, bandit.plugins
#bandit.core.test_properties, bandit.core.test_properties.checks
#bandit.core.utils.check_ast_node


def cli(args_=None):
    parser = _get_parser()
    args = vars(parser.parse_args(args_))

    # Find the source code paths to modify
    if fil := args.get('file'):
        fil = fil.resolve()
        paths = [fil]
        dir_ = fil.parent
    else:
        if dir_ := args.get('directory'):
            dir_ = dir_.resolve()
            paths = get_paths(dir_)
            
        elif module := args.get('module'):
            dir_, paths = get_module_files(module)

        for p in paths:
            print(str(p.relative_to(dir_)))

        if not confirm_action('Continue with above paths?'):
            sys.exit(0)

    modify(dir_=dir_, paths=paths, **args)




if __name__ == '__main__':
    cli()
