#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = utils
# author=KGerring
# date = 6/12/21
# project poetryproj
# docs root 
"""
 poetryproj  

"""
from __future__ import annotations

import importlib
import inspect
import io
import json
import os
import pkgutil
import textwrap
import tokenize
from pathlib import Path
from types import ModuleType
from typing import AnyStr, Dict, Iterable, List, Optional, Set, Type, Union
import codecs
from attr import dataclass
from fixit.common.base import CstLintRule, LintConfig
from . import config  # LintConfig
import os  # isort:skip
import re  # isort:skip

LintRuleCollectionT = Set[Union[Type[CstLintRule], Type['PseudoLintRule']]]

DEFAULT_FILENAME: str = "not/a/real/file/path.py"

DEFAULT_CONFIG: LintConfig = LintConfig(
		repo_root=str(Path(__file__).parent.parent),  # Set base config repo_root to `fixit` directory for testing.
)

def _dedent(src: str) -> str:
	src = re.sub(r"\A\n", "", src)
	return textwrap.dedent(src)

def _detect_encoding(source: bytes) -> str:
	"""

	:param bytes source:
	:type source:
	:return:
	:rtype:
	"""
	return tokenize.detect_encoding(io.BytesIO(source).readline)[0]

def descendents(class_: type):
	"""
	Return a list of the class hierarchy below (and including) the given class.

	The list is ordered from least- to most-specific.  Can be useful for
	printing the contents of an entire class hierarchy.
	"""
	assert isinstance(class_, type)
	q = [class_]
	out = []
	while len(q):
		x = q.pop(0)
		out.insert(0, x)
		for b in x.__subclasses__():
			if b not in q and b not in out:
				q.append(b)
	return out[::-1]

def maybe_pathlib(path: Optional[Path, str]):
	if isinstance(path, Path):
		return path
	elif isinstance(path, str):
		if os.path.exists(path):
			return Path(path)
		return Path().cwd()
	return path

def auto_encode(string: AnyStr, encoding: str = "utf-8", errors: str = "strict") -> bytes:
	"""Lookup a encoder and encode the string if it is bytes, else return it
	untouched if it's already in bytes (for utf). If its an int, etc, it'll try
	to wrap it in bytes for you.

	:param string: The text to encode
	:param encoding: The encoding-type to use; default is `utf-8`
	:param errors: optional; pass `replace` or `namereplace` if you don't want
									the default `strict` for how to process errors
	:return: The encoded text
	"""
	encoder = codecs.getencoder(encoding=encoding)
	if isinstance(string, bytes):
		return string
	elif isinstance(string, str):
		return encoder(string)[0]
	else:
		return encoder(str(string))[0]

def auto_decode(string: AnyStr, encoding: str = "utf-8", errors: str = "strict") -> str:
	"""Lookup a decoder and decode the bytestring if it is str, else return it
	untouched if it's already in bytes (for utf). If its an int, etc, it'll try
	to wrap it in str for you.

	:param string: The bytestring to decode
	:param encoding: the encoding to use; default=`utf-8`
	:param errors: optional; use `replace` or `namereplace`, etc if you don't want
									`strict`, the default
	:return: a decoded string of type `str`
	"""
	decoder = codecs.getdecoder(encoding=encoding)
	if isinstance(string, str):
		return string
	elif isinstance(string, bytes):
		return decoder(string)[0]
	else:
		return str(string)

def commonpath(path1: Path, path2: Path) -> Optional[Path]:
	"""Return the common part shared with the other path, or None if there is
	no common part.

	If one path is relative and one is absolute, returns None.
	"""
	try:
		return Path(os.path.commonpath((str(path1), str(path2))))
	except ValueError:
		return None

def get_common_ancestor(paths: Iterable[Path]) -> Path:
	"""
	Get the common ancestor of the paths if it exists
	:param paths:
	:return:
	:rtype:
	"""
	if not all(isinstance(p, Path) for p in paths):
		paths = list(map(Path, paths))
	
	common_ancestor: Optional[Path] = None
	for path in paths:
		if not path.exists():
			continue
		if common_ancestor is None:
			common_ancestor = path
		else:
			if common_ancestor in path.parents or path == common_ancestor:
				continue
			elif path in common_ancestor.parents:
				common_ancestor = path
			else:
				shared = commonpath(path, common_ancestor)
				if shared is not None:
					common_ancestor = shared
	if common_ancestor is None:
		common_ancestor = Path.cwd()
	elif common_ancestor.is_file():
		common_ancestor = common_ancestor.parent
	return common_ancestor

def is_rule(obj: object) -> bool:
	if inspect.isabstract(obj):
		return False
	# elif getattr(obj, "_is_rule", False):
	#    logger.debug(f"is rule {obj}")
	#    return True
	
	if inspect.isclass(obj):
		if issubclass(obj, CstLintRule) and obj is not CstLintRule:
			return True
		if obj is not CstLintRule and (issubclass(obj, CstLintRule) or issubclass(obj, PseudoLintRule)):
			return True
	
	return False

class TestCase:
	code: str
	filename: str = DEFAULT_FILENAME
	config: LintConfig = DEFAULT_CONFIG

@dataclass
class ValidTestCase(TestCase):
	"""
	/Users/kristen/repos/Fixit/fixit/common/utils.py
	"""
	code: str
	filename: str = DEFAULT_FILENAME
	config: LintConfig = DEFAULT_CONFIG

@dataclass
class InvalidTestCase(TestCase):
	code: str
	kind: Optional[str] = None
	line: Optional[int] = None
	column: Optional[int] = None
	expected_replacement: Optional[str] = None
	filename: str = DEFAULT_FILENAME
	config: LintConfig = DEFAULT_CONFIG
	expected_message: Optional[str] = None
	
	@property
	def expected_str(self) -> str:
		return f"{_str_or_any(self.line)}:{_str_or_any(self.column)}: {self.kind} ..."

def import_submodules(package: str, recursive: bool = True) -> Dict[str, ModuleType]:
	""" Import all submodules of a module, recursively, including subpackages. """
	package: ModuleType = importlib.import_module(package)
	results = {}
	for _loader, name, is_pkg in pkgutil.walk_packages(package.__path__):
		full_name = package.__name__ + "." + name
		try:
			results[full_name] = importlib.import_module(full_name)
		except ModuleNotFoundError:
			pass
		if recursive and is_pkg:
			results.update(import_submodules(full_name))
	return results


def import_distinct_rules_from_package(
		package: str,
		block_list_rules: List[str] = [],
		seen_names: Optional[Set[str]] = None,
		allow_list_rules: Optional[List[str]] = None,
) -> LintRuleCollectionT:
	"""Import all rules from the specified package, omitting rules that appear in the block list.
		Raises error on repeated rule names.
		Optional parameter `seen_names` accepts set of names that should not occur in this package.
	:param package:
	:param block_list_rules:
	:param set seen_names: a set of names that should not occur in this package.
	:param list allow_list_rules:
	:return:
	:rtype:
	:raises: exceptions.DuplicateLintRuleNameError
	"""
	# Import all rules from the specified package, omitting rules that appear in the block list.
	# Raises error on repeated rule names.
	# Optional parameter `seen_names` accepts set of names that should not occur in this package.
	rules: LintRuleCollectionT = set()
	if seen_names is None:
		seen_names: Set[str] = set()
	for _module_name, module in import_submodules(package).items():
		for name in dir(module):
			try:
				obj = getattr(module, name)
				if inspect.isclass(obj) and hasattr(obj, "_is_rule"):
					#print(obj)
					if name in seen_names:
						raise exceptions.DuplicateLintRuleNameError(
								f"Lint rule name {name!r} is duplicated."
						)
					seen_names.add(name)
					# For backwards compatibility if `allow_list_rules` is missing fall back to all allowed
					if not allow_list_rules or name in allow_list_rules:
						if name not in block_list_rules:
							rules.add(obj)
			
			except (TypeError, Exception):
				print(f"{module}, {name}")
				continue
	return rules

def import_rule_from_package(
		package_name: str,
		rule_class_name: str,
) -> Optional[LintRuleT]:
	"""Imports the first rule with matching class name found in specified package.
	:param str package_name: fixit.rules
	:param str rule_class_name: UseTypesFromTypingRule
	:return:
	:rtype:
	"""
	# Imports the first rule with matching class name found in specified package.
	rule: Optional[LintRuleT] = None
	package = importlib.import_module(package_name)
	for _loader, name, is_pkg in pkgutil.walk_packages(
			getattr(package, "__path__", None)
	):
		full_package_or_module_name = package.__name__ + "." + name
		try:
			module = importlib.import_module(full_package_or_module_name)
			rule = getattr(module, rule_class_name, None)
		except ModuleNotFoundError:
			pass
		if is_pkg:
			rule = import_rule_from_package(
					full_package_or_module_name, rule_class_name
			)
		
		if rule is not None:
			# Stop early if we have found the rule.
			return rule
	return rule

def find_and_import_rule(
		rule_class_name: str,
		packages: List[str]
) -> LintRuleT:
	for package in packages:
		imported_rule = import_rule_from_package(package, rule_class_name)
		if imported_rule is not None:
			return imported_rule
	
	# If we get here, the rule was not found.
	raise exceptions.LintRuleNotFoundError(
			f"Could not find lint rule {rule_class_name} in the following packages: \n"
			+ "\n".join(packages)
	)


if __name__ == '__main__':
	print(__file__)
