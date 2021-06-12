#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" 
$ 
"""

from __future__ import annotations  # isort:skip
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Type

DictStrAny = Dict[str, Any]

def cls_kwargs(cls: ErrorMixin, ctx: DictStrAny) -> ErrorMixin:
	return cls(**ctx)

class ErrorMixin:
	code: str
	msg_template: str
	
	def __init__(self, **ctx: Any) -> None:
		self.__dict__ = ctx
	
	def __str__(self) -> str:
		return self.msg_template.format(**self.__dict__)
	
	def __reduce__(self):
		return cls_kwargs, (self.__class__, self.__dict__)
		# -> Tuple[Callable[..., ErrorMixin],
		#Tuple[ErrorMixin, DictStrAny]:

class Error(Exception):
	pass

class DuplicateLintRuleNameError(Error):
	"""
	from utils
	"""
	name: str = ""
	pass

class FixtureFileNotFoundError(Error):
	"""
	from utils
	"""
	filename = ""
	msg = f"Fixture file not found at {filename}. "
	msg += "Please run `python -m fixit.common.generate_pyre_fixtures <rule>` to generate fixtures."
	pass

class LintRuleNotFoundError(Error):
	"""
	from utils
	"""
	packages: list[str] = ["fixit.dev_rules", "fixit.rules"]
	#rule_class_name: str
	_template = "Could not find lint rule {rule_class_name} in the following packages: \n"
	# + "\n".join(packages)
	pass

class RuleNotTypeDependentError(Error):
	"""
	from generate_pyre_fixtures.py
	"""
	pass

class RuleTypeError(Error):
	"""
	from generate_pyre_fixtures.py
	"""
	pass

class PyreQueryError(Error):
	"""
	from generate_pyre_fixtures.py
	"""
	def __init__(self, command: str, message: str) -> None:
		super().__init__("Unable to infer types from temporary file. " + f"Command `{command}` returned with the following message: {message}.")












__all__ = sorted(
		[getattr(v, '__name__', k)
		 for k, v in list(globals().items())  # export
		 if ((callable(v) and getattr(v, "__module__", "") == __name__  # callables from this module
		      or k.isupper()) and  # or CONSTANTS
		     not str(getattr(v, '__name__', k)).startswith('__'))]
)  # neither marked internal

if __name__ == '__main__':
	print(__file__)
