#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""



===================  ============================
name                 type
===================  ============================
allow_list_rules     List[str]
block_list_patterns  List[str]
block_list_rules     List[str]
fixture_dir          str
use_noqa             bool
formatter            List[str]
packages             List[str]
repo_root            str
rule_config          Dict[str, Dict[str, object]]
filename             Optional[str]
===================  ============================

"""

from __future__ import annotations

import distutils.spawn
import importlib.resources as pkg_resources
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type, Union

import yaml
from attr import dataclass, field
from jsonschema import validate
from loguru import logger

from .utils import LintRuleCollectionT, import_distinct_rules_from_package

import sys  # isort:skip
import os  # isort:skip

LINT_CONFIG_FILE_NAME: Path = Path(".fixit.config.yaml")
LINT_CONFIG_SCHEMA_NAME: str = 'config.schema.json'
LINT_CONFIG_TOML_NAME: Path = LINT_CONFIG_FILE_NAME.with_suffix(".toml")

PATH_SETTINGS = ["repo_root", "fixture_dir"]
DEFAULT_FORMATTER = ["black", "-"]
DEFAULT_PACKAGES = ["metaproj.rules"]
DEFAULT_PATTERNS = [f"@ge{''}nerated", "@nolint"]

@dataclass(getstate_setstate=True, slots=True, weakref_slot=True,)
class LintConfig:
	allow_list_rules: List[str] = field(factory=list)
	block_list_patterns: List[str] = field(factory=lambda: DEFAULT_PATTERNS)
	block_list_rules: List[str] = field(factory=list)
	fixture_dir: str = "./fixtures"
	use_noqa: bool = False
	formatter: List[str] = field(factory=list)
	packages: List[str] = field(factory=lambda: DEFAULT_PACKAGES)
	repo_root: str = "."
	rule_config: Dict[str, Dict[str, object]] = field(factory=dict)
	filename: Optional[str] = field(default=".")
	

def get_validated_settings(
		file_content: Dict[str, Any],
		current_dir: Path
) -> Dict[str, Any]:
	# __package__ should never be none (config.py should not be run directly)
	# But use .get() to make pyre happy
	pkg = globals().get("__package__")
	assert pkg, "No package was found, config types not validated."
	config = pkg_resources.read_text(pkg, LINT_CONFIG_SCHEMA_NAME)
	# Validates the types and presence of the keys
	schema = json.loads(config)
	validate(instance=file_content, schema=schema)
	for path_setting_name in PATH_SETTINGS:
		if path_setting_name in file_content:
			setting_value = file_content[path_setting_name]
			abspath: Path = (current_dir / setting_value).resolve()
		else:
			abspath: Path = current_dir
		# Set path setting to absolute path.
		file_content[path_setting_name] = str(abspath)
	return file_content

@lru_cache()
def get_lint_config() -> LintConfig:
	config = {}
	filename = ""
	cwd = Path.cwd()
	for directory in (cwd, *cwd.parents):
		# Check for config file.
		possible_config = directory / LINT_CONFIG_FILE_NAME
		if possible_config.is_file():
			with open(possible_config, "r") as f:
				file_content = yaml.safe_load(f.read())
			
			if isinstance(file_content, dict):
				config = get_validated_settings(file_content, directory)
				break
	
	# Find formatter executable if there is one.
	formatter_args = config.get("formatter", DEFAULT_FORMATTER)
	exe = distutils.spawn.find_executable(formatter_args[0]) or formatter_args[0]
	formatter_args[0] = os.path.abspath(exe)
	config["formatter"] = formatter_args
	# Missing settings will be populated with defaults.
	return LintConfig(**config)

def gen_config_file() -> None:
	# Generates a `.fixit.config.yaml` file with defaults in the current working dir.
	config_file = LINT_CONFIG_FILE_NAME.resolve()
	default_config_dict = asdict(LintConfig())
	with open(config_file, "w") as cf:
		yaml.dump(default_config_dict, cf)

def print_config_file() -> None:
	default_config_dict = asdict(LintConfig())
	print(yaml.dump(default_config_dict))

def get_rules_from_config(config: Optional[LintConfig] = None) -> LintRuleCollectionT:
	# Get rules from the packages specified in the lint config file, omitting block-listed rules.
	lint_config: LintConfig = config or get_lint_config()
	rules: LintRuleCollectionT = set()
	all_names: Set[str] = set()
	for package in lint_config.packages:
		rules_from_pkg = import_distinct_rules_from_package(
				package,
				lint_config.block_list_rules,
				all_names,
				lint_config.allow_list_rules,
		)
		rules.update(rules_from_pkg)
	return rules


__all__ = sorted(
		[getattr(v, '__name__', k)
		 for k, v in list(globals().items())  # export
		 if ((callable(v) and getattr(v, "__module__", "") == __name__  # callables from this module
		      or k.isupper()) and  # or CONSTANTS
		     not str(getattr(v, '__name__', k)).startswith('__'))]
)  # neither marked internal

if __name__ == '__main__':
	print(__file__)
