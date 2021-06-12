#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = testing
# author=KGerring
# date = 6/12/21
# project poetryproj
# docs root 
"""
 poetryproj  

"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import new_class
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Type, Union, cast

import click
from attr import dataclass
from fixit.cli.args import import_rule
from fixit.common.base import CstLintRule, LintRuleT
from fixit.common.utils import _dedent
from fixit.rule_lint_engine import lint_file
from libcst.metadata import MetadataWrapper
from libcst.metadata.type_inference_provider import PyreData, _process_pyre_data, run_command
from loguru import logger

from . import base, exceptions
from .autofix import LintPatch
from .report import BaseLintRuleReport
from .utils import InvalidTestCase, LintRuleCollectionT, ValidTestCase, _dedent

CONFIG_SOURCES = ('.isort.cfg',
                  'pyproject.toml',
                  'setup.cfg',
                  'tox.ini',
                  '.editorconfig')


CstLintRule = base.CstLintRule

TestCaseT = Union[ValidTestCase, InvalidTestCase]

def get_fixture_path(
		fixture_top_dir: Path,
		rule_module: str,
		rules_package: str
) -> Path:
	"""

	:param Path fixture_top_dir:
	:param str rule_module:
	:param str rules_package:
	:return:
	:rtype: Path
	"""
	#'/Users/kristen/repos/Fixit/fixit/tests/fixtures'
	subpackage: str = rule_module.split(f"{rules_package}.", 1)[-1]
	fixture_subdir = subpackage.replace(".", "/")
	return fixture_top_dir / fixture_subdir

def gen_types_for_test_case(source_code: str, dest_path: Path) -> None:
	rule_fixture_subdir: Path = dest_path.parent
	if not rule_fixture_subdir.exists():
		rule_fixture_subdir.mkdir(parents=True)
	with tempfile.NamedTemporaryFile("w", dir=rule_fixture_subdir, suffix=".py") as temp:
		temp.write(_dedent(source_code))
		temp.seek(0)
		import shlex
		
		cmd = f'''pyre query "types(path='{temp.name}')"'''
		stdout, stderr, return_code = run_command(cmd)
		if return_code != 0:
			raise exceptions.PyreQueryError(cmd, f"{stdout}\n{stderr}")
		data = json.loads(stdout)
		# Check if error is a key in `data` since pyre may report errors this way.
		if "error" in data:
			raise exceptions.PyreQueryError(cmd, data["error"])
		data = data["response"][0]
		data: PyreData = _process_pyre_data(data)
		print(f"Writing output to {dest_path}")
		res = json.dumps({"types": data["types"]}, indent=2)
		dest_path.write_text(res)

def gen_types(rule: CstLintRule, rule_fixture_dir: Path) -> None:
	if not rule.requires_metadata_caches():
		raise exceptions.RuleNotTypeDependentError("Rule does not list any cache-dependent providers in its `METADATA_DEPENDENCIES`.")
	if hasattr(rule, "VALID") or hasattr(rule, "INVALID"):
		print("Starting pyre server")
		stdout, stderr, return_code = run_command("pyre start")
		if return_code != 0:
			print(stdout)
			print(stderr)
		else:
			class_name = getattr(rule, "__name__")
			if hasattr(rule, "VALID"):
				for idx, valid_tc in enumerate(getattr(rule, "VALID")):
					path: Path = rule_fixture_dir / f"{class_name}_VALID_{idx}.json"
					gen_types_for_test_case(source_code=valid_tc.code, dest_path=path)
			if hasattr(rule, "INVALID"):
				for idx, invalid_tc in enumerate(getattr(rule, "INVALID")):
					path: Path = rule_fixture_dir / f"{class_name}_INVALID_{idx}.json"
					gen_types_for_test_case(source_code=invalid_tc.code, dest_path=path)
			run_command("pyre stop")

def gen_type_inference_wrapper(code: str, pyre_fixture_path: Path) -> MetadataWrapper:
	"""
	 :param str code:
	 :param Path pyre_fixture_path:
	 :return:
	 :rtype: MetadataWrapper
	 """
	# Given test case source code and a path to a pyre fixture file, generate a MetadataWrapper for a lint rule test case.
	module: cst.Module = cst.parse_module(_dedent(code))
	provider_type = TypeInferenceProvider
	try:
		pyre_json_data: PyreData = json.loads(pyre_fixture_path.read_text())
	except FileNotFoundError as e:
		raise exceptions.FixtureFileNotFoundError(
				f"Fixture file not found at {e.filename}. " + "Please run `python -m "
				                                              "fixit.common.generate_pyre_fixtures <rule>` to generate fixtures.")
	return MetadataWrapper(
			module=module,
			cache={cast(Type[BaseMetadataProvider[object]], provider_type): pyre_json_data},
	)

def validate_patch(report: BaseLintRuleReport, test_case: InvalidTestCase) -> None:
	patch: Optional[LintPatch] = report.patch
	expected_replacement: Optional[str] = test_case.expected_replacement
	
	if patch is None:
		if expected_replacement is not None:
			raise AssertionError("The rule for this test case has no auto-fix, but expected source was specified.")
		return
	if expected_replacement is None:
		raise AssertionError("The rule for this test case has an auto-fix, but no expected source was specified.")
	
	expected_replacement: str = _dedent(expected_replacement)
	patched_code: str = patch.apply(_dedent(test_case.code))
	if patched_code != expected_replacement:
		raise AssertionError(
				"Auto-fix did not produce expected result.\n" + f"Expected:\n{expected_replacement}\n" + f"But found:\n{patched_code}"
		)
	logger.debug(str(report))
	

@dataclass(frozen=False)
class TestCasePrecursor:
	rule: Type[CstLintRule] = None
	test_methods: Mapping[str, TestCaseT] = {}
	fixture_paths: Mapping[str, Path] = {}

class LintRuleTestCase(unittest.TestCase):
	#tearDownClass, setUpClass, tearDown, setUp
	#_testMethodName
	
	def _test_method(
			self,
			test_case: TestCaseT,
			rule: Type[CstLintRule],
			fixture_file: Optional[Path] = None,
	) -> None:
		cst_wrapper: Optional[MetadataWrapper] = None
		if fixture_file is not None:
			cst_wrapper = gen_type_inference_wrapper(test_case.code, fixture_file)
		
		reports = lint_file(
				Path(test_case.filename),
				_dedent(test_case.code).encode("utf-8"),
				rules={rule},
				cst_wrapper=cst_wrapper,
				config=test_case.config,
		)
		if isinstance(test_case, ValidTestCase):
			self.assertEqual(
					len(reports),
					0,
					'Expected zero reports for this "valid" test case. Instead, found:\n' + "\n".join(str(e) for e in reports),
			)
		
		else:
			self.assertGreater(
					len(reports),
					0,
					f'Expected a report for this "invalid" test case but `self.report` was not called:\n'
					+ test_case.code,
			)
			self.assertLessEqual(
					len(reports),
					1,
					'Expected one report from this "invalid" test case. Found multiple:\n' + "\n".join(str(e) for e in reports),
			)
			report = reports[0]
			
			if not (test_case.line is None or test_case.line == report.line):
				raise AssertionError(
						f"Expected line: {test_case.line} but found line: {report.line}")
			
			if not (test_case.column is None or test_case.column == report.column):
				raise AssertionError(
						f"Expected column: {test_case.column} but found column: {report.column}"
				)
			
			kind = test_case.kind if test_case.kind is not None else rule.__name__
			if kind != report.code:
				raise AssertionError(
						f"Expected:\n    {test_case.expected_str}\nBut found:\n    {report}"
				)
			if (
					test_case.expected_message is not None
					and test_case.expected_message != report.message
			):
				raise AssertionError(
						f"Expected message:\n    {test_case.expected_message}\nBut got:\n    {report.message}"
				)
			
			validate_patch(report, test_case)

def _gen_test_methods_for_rule(
		rule: Type[CstLintRule],
		fixture_dir: Path,
		rules_package: str
) -> TestCasePrecursor:
	"""Aggregates all of the cases inside a single CstLintRule's VALID and INVALID attributes
	and maps them to altered names with a `test_` prefix so that 'unittest' can discover them
	later on and an index postfix so that individual tests can be selected from the command line.

	:param CstLintRule rule:
	:param Path fixture_dir:
	:param str rules_package:
	:returns:
	:rtype: TestCasePrecursor
	"""
	
	valid_tcs = {}
	invalid_tcs = {}
	requires_fixtures = False
	fixture_paths: Dict[str, Path] = {}
	fixture_subdir: Path = get_fixture_path(fixture_dir, rule.__module__, rules_package)
	
	if issubclass(rule, CstLintRule):
		if rule.requires_metadata_caches():
			requires_fixtures = True
		if hasattr(rule, "VALID"):
			for idx, test_case in enumerate(getattr(rule, "VALID")):
				name = f"test_VALID_{idx}"
				valid_tcs[name] = test_case
				if requires_fixtures:
					fixture_paths[name] = fixture_subdir / f"{rule.__name__}_VALID_{idx}.json"
		if hasattr(rule, "INVALID"):
			for idx, test_case in enumerate(getattr(rule, "INVALID")):
				name = f"test_INVALID_{idx}"
				invalid_tcs[name] = test_case
				if requires_fixtures:
					fixture_paths[name] = fixture_subdir / f"{rule.__name__}_INVALID_{idx}.json"
	
	return TestCasePrecursor(
			rule=rule,
			test_methods={**valid_tcs, **invalid_tcs},
			fixture_paths=fixture_paths,
	)

def _gen_all_test_methods(
		rules: LintRuleCollectionT,
		fixture_dir: Path,
		rules_package: str
) -> Sequence[TestCasePrecursor]:
	"""
	Converts all passed-in lint rules to type `TestCasePrecursor` to ease further TestCase
	creation later on.

	"""
	cases = []
	for rule in rules:
		if not issubclass(rule, CstLintRule):
			continue
		test_cases_for_rule = _gen_test_methods_for_rule(cast(Type[CstLintRule], rule), fixture_dir, rules_package)
		cases.append(test_cases_for_rule)
	return cases

def make_lint_rule_test(
		test_case: TestCasePrecursor,
		test_case_type: Type[unittest.TestCase] = LintRuleTestCase,
		custom_test_method_name: str = "_test_method",
) -> None:
	"""Generates classe.
	:param rule: A class extending `CstLintRule` to be converted to test case.
	:param LintRuleTestCase test_case_type: A class extending Python's `unittest.TestCase` that implements
		a custom test method for testing lint rules to  serve as a stencil for test cases.
	:param TestCasePrecursor test_case: The collection of methods for a rule via _gen_test_methods_for_rule
	New classes will be generated, and named after each lint rule.
		They will inherit directly from the class passed into `test_case_type`.
	If argument is omitted, will default to the `LintRuleTestCase` class from fixit.common.testing.

	:param str custom_test_method_name: A member method of the class passed into `test_case_type`
		parameter that contains the logic around asserting success or failure of CstLintRule's `ValidTestCase` and `InvalidTestCase` test cases. The method will be dynamically renamed to
		`test_<VALID/INVALID>_<test case index>` for discovery by unittest.

		If argument is omitted, `add_lint_rule_tests_to_module` will look for a test method named `_test_method` member of `test_case_type`.
	The structure of the fixture directory is automatically assumed to mirror the structure of the rules package, eg: `<rules_package>.submodule.module.rule_class` should
		have fixture files in `<fixture_dir>/submodule/module/rule_class/`.

	"""
	test_methods_to_add: Dict[str, Callable] = {}
	rule_name: str = test_case.rule.__name__
	logger.debug(f'rule_name = {rule_name!r}')
	for test_method_name, test_method_data in test_case.test_methods.items():
		fixture_file: Optional[Path] = test_case.fixture_paths.get(test_method_name)
		
		def test_method(
				self: Type[unittest.TestCase],
				data: Union[ValidTestCase, InvalidTestCase] = test_method_data,
				rule: Type[CstLintRule] = test_case.rule,
				fixture_file: Optional[str] = fixture_file,
		) -> None:
			return getattr(self, custom_test_method_name)(data, rule, fixture_file)
		
		test_method.__name__ = test_method_name
		test_methods_to_add[test_method_name] = test_method
	try:
		test_case_class = new_class(rule_name, (test_case_type,), test_methods_to_add)
		return {rule_name: test_case_class}
	except Exception:
		return test_methods_to_add

def add_lint_rule_tests_to_module(
		module_attrs: Dict[str, Any],
		rules: LintRuleCollectionT,
		test_case_type: Type[unittest.TestCase] = LintRuleTestCase,
		custom_test_method_name: str = "_test_method",
		fixture_dir: Path = Path("/Users/kristen/repos/Fixit/fixit/tests/fixtures"),
		rules_package: str = "fixit.rules",
) -> None:
	"""Generates classes.
	Generates classes inheriting from `unittest.TestCase` from the data available in `rules` and
	adds these to `module_attrs`.
	The goal is to facilitate unit test discovery by Python's `unittest` framework.
	This will provide the capability of
	testing your lint rules by running commands such as `python -m unittest <your testing module name>`.

	:param module_attrs: A dictionary of attributes we want to add these test cases to.
		If adding to a module, you can pass `globals()` as the argument.

	:param rules: A collection of classes extending `CstLintRule` to be converted to test cases.

	:param LintRuleTestCase test_case_type: A class extending Python's `unittest.TestCase` that implements
		a custom test method for testing lint rules to  serve as a stencil for test cases.

	New classes will be generated, and named after each lint rule.
		They will inherit directly from the class passed into `test_case_type`.
	If argument is omitted, will default to the `LintRuleTestCase` class from fixit.common.testing.

	:param str custom_test_method_name: A member method of the class passed into `test_case_type`
		parameter that contains the logic around asserting success or failure of CstLintRule's `ValidTestCase` and `InvalidTestCase` test cases. The method will be dynamically renamed to
		`test_<VALID/INVALID>_<test case index>` for discovery by unittest. If argument is omitted, `add_lint_rule_tests_to_module` will look for a test method named `_test_method` member of `test_case_type`.

	:param Path fixture_dir: The directory in which fixture files for the passed rules live.
		Necessary only if any lint rules require fixture data for testing.

	:param str rules_package: The name of the rules package.
		This will be used during the search for fixture files and provides insight into the structure of the fixture directory.

	The structure of the fixture directory is automatically assumed to mirror the structure of the rules package, eg: `<rules_package>.submodule.module.rule_class` should
		have fixture files in `<fixture_dir>/submodule/module/rule_class/`.

	"""
	for test_case in _gen_all_test_methods(rules, fixture_dir, rules_package):
		rule_name: str = test_case.rule.__name__
		test_methods_to_add: Dict[str, Callable] = {}
		
		for test_method_name, test_method_data in test_case.test_methods.items():
			fixture_file: Path = test_case.fixture_paths.get(test_method_name)
			
			def test_method(
					self: Type[unittest.TestCase],
					data: Union[ValidTestCase, InvalidTestCase] = test_method_data,
					rule: Type[CstLintRule] = test_case.rule,
					fixture_file: Optional[str] = fixture_file,
			) -> None:
				return getattr(
						self, custom_test_method_name
				)(data, rule, fixture_file)
			
			test_method.__name__ = test_method_name
			test_methods_to_add[test_method_name] = test_method
		
		test_case_class = new_class(rule_name, (test_case_type,), test_methods_to_add)
		module_attrs[rule_name] = test_case_class

def gen_types(rule: CstLintRule, rule_fixture_dir: Path) -> None:
	if not rule.requires_metadata_caches():
		raise exceptions.RuleNotTypeDependentError("Rule does not list any cache-dependent providers in its `METADATA_DEPENDENCIES`.")
	if hasattr(rule, "VALID") or hasattr(rule, "INVALID"):
		print("Starting pyre server")
		stdout, stderr, return_code = run_command("pyre start")
		if return_code != 0:
			print(stdout)
			print(stderr)
		else:
			class_name = getattr(rule, "__name__")
			if hasattr(rule, "VALID"):
				for idx, valid_tc in enumerate(getattr(rule, "VALID")):
					path: Path = rule_fixture_dir / f"{class_name}_VALID_{idx}.json"
					gen_types_for_test_case(source_code=valid_tc.code, dest_path=path)
			if hasattr(rule, "INVALID"):
				for idx, invalid_tc in enumerate(getattr(rule, "INVALID")):
					path: Path = rule_fixture_dir / f"{class_name}_INVALID_{idx}.json"
					gen_types_for_test_case(source_code=invalid_tc.code, dest_path=path)
			run_command("pyre stop")

@click.command(short_help="Generate fixture files required to run unit tests on `TypeInference`-dependent lint rules.")
@click.pass_context
@click.option(
		"--rule",
		"rule",
		default="fixit.rules.add_file_header.AddMissingHeaderRule",
		help="The name of your lint rule class or the full dotted path to your lint rule class. (e.g. `NoAssertEqualsRule` or " "`fixit.rules.no_assert_equals.NoAssertEqualsRule`)",
		callback=import_rule,
)
@click.option(
		"--fixture-dir",
		"fixture_dir",
		envvar="FIXTURE_DIR",
		default="/Users/kristen/repos/Fixit/fixit/tests/fixtures",
		type=(lambda p: Path(p).resolve(strict=True)),
		help="Main fixture file directory for integration testing.",
)  # Path(p).resolve(strict=True))
@click.option("--rules-package", "rules_package", default="fixit.rules", help="Full dotted path of a package containing lint rules.")
def run_main(ctx, rule, fixture_dir, rules_package="fixit.rules"):
	"""
	Run this script directly to generate pyre data for a lint rule that requires TypeInferenceProvider metadata.
	use_is_none_on_optional

	"""
	rule: LintRuleT
	fixture_dir: Path = fixture_dir
	fixture_path: Path = get_fixture_path(fixture_dir, rule.__module__, rules_package)
	if not issubclass(rule, CstLintRule):
		raise exceptions.RuleTypeError("Rule must inherit from CstLintRule.")
	gen_types(cast(CstLintRule, rule), fixture_path)
	


if __name__ == '__main__':
	run_main()
