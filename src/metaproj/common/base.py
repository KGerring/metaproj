#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
base module


#ContextAwareTransformer.transform_module_impl
#CodemodCommand._instantiate_and_run
#CodemodCommand.transform_module_impl
#CodemodCommand.transform_module
#   CodemodCommand.transform_module
# CodemodCommand._instantiate_and_run
# Codemod._handle_metadata_reference

"""
from __future__ import annotations
import sys
import contextlib
import dataclasses
import inspect
import re
from abc import ABC, ABCMeta
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Collection, Dict, List, Optional, Protocol, Tuple, Type, Union

import libcst
import libcst.codemod as codemod
import libcst.metadata as metadata

from attr import dataclass
from libcst._metadata_dependent import MetadataDependent
from libcst.codemod.visitors._remove_imports import RemoveImportsVisitor
from loguru import logger

print(f'uncomment out the imports!!!!!! line 35 {__file__}', file = sys.stderr)

#from libcst import _batched_visitor, _metadata_dependent

from libcst.codemod import (Codemod,
                            CodemodCommand,
                            CodemodContext,
                            ContextAwareTransformer,
                            VisitorBasedCodemodCommand,
)


#AddImportsVisitor, RemoveImportsVisitor

#from libcst.metadata import ( BaseMetadataProvider, BatchableMetadataProvider,
#                              CodePosition, MetadataWrapper, ParentNodeProvider, PositionProvider, TypeInferenceProvider,)

TypeInferenceProvider = metadata.TypeInferenceProvider
PositionProvider = metadata.PositionProvider

from libcst.metadata.name_provider import FullyQualifiedNameProvider

from . import exceptions
from .report import BaseLintRuleReport, CstLintRuleReport

if TYPE_CHECKING:
	from libcst.metadata.base_provider import ProviderT

CACHE_DEPENDENT_PROVIDERS: Tuple["ProviderT"] = (TypeInferenceProvider, FullyQualifiedNameProvider)

LintRuleT:  Union[Type['CstLintRule'], ['PseudoLintRule']]

metadata: Mapping["ProviderT", Mapping["CSTNode", object]]

METADATA_DEPENDENCIES: ClassVar[Collection["ProviderT"]] = ()

FilePathT = Union[Path, str]

exceptions = exceptions.Error

class ProviderEnsuranceMetaclass(ABCMeta):
	def __new__(mcls, name, bases, namespace, **kwargs):
		providers = namespace.get("METADATA_DEPENDENCIES", ())
		if PositionProvider not in providers:
			namespace["METADATA_DEPENDENCIES"] = (PositionProvider,) + providers
		return super().__new__(mcls, name, bases, namespace, **kwargs)

class extendabletype(type):
	"""A type with a syntax trick: 'class __extend__(t)' actually extends
	the definition of 't' instead of creating a new subclass.
	exec_body(ns)
	_calculate_meta(meta, bases)
	"""
	def __new__(cls, name, bases, dict):
		if name == "__extend__":
			for cls in bases:
				for key, value in list(dict.items()):
					if key == "__module__":
						continue
					# XXX do we need to provide something more for pickling?
					setattr(cls, key, value)
			return None
		else:
			return super().__new__(cls, name, bases, dict)

def get_inherited_dependencies(cls) -> Collection["ProviderT"]:
	import inspect
	
	dependencies = set()
	for c in inspect.getmro(cls):
		if issubclass(c, MetadataDependent):
			dependencies.update(c.METADATA_DEPENDENCIES)
	return frozenset(dependencies)

class BaseRuleMixin(ABC):
	#: a short message in one or two sentences show to user when the rule is violated.
	MESSAGE: Optional[str] = None
	METADATA_DEPENDENCIES: Tuple[Type[BaseMetadataProvider], ...] = (
			PositionProvider,
	)
	def should_skip_file(self) -> bool:
		return False
	
	@classmethod
	def requires_metadata_caches(cls) -> bool:
		return any(p in CACHE_DEPENDENT_PROVIDERS for p in cls.get_inherited_dependencies())
	
	@classmethod
	def get_inherited_dependencies(cls) -> Collection["ProviderT"]:
		"""
		Returns all metadata dependencies declared by classes in the MRO of ``cls``
			that subclass this class.

		Recursively searches the MRO of the subclass for metadata dependencies.
		"""
		import inspect
		dependencies = set()
		for c in inspect.getmro(cls):
			if issubclass(c, MetadataDependent):
				dependencies.update(c.METADATA_DEPENDENCIES)
		return frozenset(dependencies)
	
	#def update_children_context(self, context: libcst.codemod.CodemodContext) -> None:
	#	for methods in self.leave_methods.values():
	#		for method in methods:
	#			method.__self__.context = context
				
	def warn(self, warning: str) -> None:
		"""
		override of Codemod.warn
		Emit a warning that is displayed to the user who has invoked this codemod.
		"""
		self.context.warnings.append(warning)

	def report(
			self,
			node: cst.CSTNode,
			message: Optional[str] = None,
			*,
			position: Optional[CodePosition] = None,
			replacement: Optional[
				Union[cst.CSTNode, cst.RemovalSentinel, cst.FlattenSentinel]
			] = None,
	) -> None:
		"""
		Report a lint violation for a given node. Optionally specify a custom
		position to report an error at or a replacement node for an auto-fix.


		"""
		if position is None:
			position = self.context.wrapper.resolve(PositionProvider)[node].start
		
		if message is None:
			message = self.MESSAGE
			if message is None:
				raise Exception(f"No lint message was provided to rule: {self}")
		report = CstLintRuleReport(
				file_path=self.context.file_path,
				node=node,
				# TODO deprecate _get_code() completely and replace with self.__class__.__name__
				code=self.__class__.__name__,
				message=message,
				line=position.line,
				# libcst columns are 0-indexed but arc is 1-indexed
				column=(position.column + 1),
				module=self.context.wrapper,
				module_bytes=self.context._source,
				replacement_node=replacement,
		)
		self.context.reports.append(report)
		
class CstLintRule(BaseRuleMixin, ContextAwareTransformer, CodemodCommand): pass
class VisitorMethod(Protocol):
	pass

def _visit_cst_rules_with_context(
		wrapper: MetadataWrapper,
		rules: Collection[Type[CstLintRule]],
		context: CstContext) -> None:
	
	rule_instances = [r(context) for r in rules]
	rule_instances = [r for r in rule_instances if not r.should_skip_file()]
	
	def before_visit(node: cst.CSTNode) -> None:
		context.node_stack.append(node)
	
	def after_leave(node: cst.CSTNode) -> None:
		context.node_stack.pop()
	
	wrapper.visit_batched(rule_instances,
						  before_visit=before_visit,
						  after_leave=after_leave
						  )

class Codemod_:
	"""
	with self._handle_metadata_reference(tree) as tree_with_metadata:
		return self.transform_module_impl(tree_with_metadata)
	"""

class _LeaveMethod(Protocol):
	__self__: "ContextAwareTransformer"
	__name__: str
	__qualname__: str
	def __call__(self, original_node: libcst.CSTNodeT,
	             updated_node: libcst.CSTNodeT) -> Union[libcst.CSTNodeT, libcst.RemovalSentinel]:
		...

class _ContextAwareTransformer(libcst.codemod.Codemod, libcst.CSTTransformer):
	"""A lean replacement of libcst.codemod.ContextAwareTransformer.

	It just extends from `libcst.CSTTransformer` and not
	`libcst.matchers.MatcherDecoratableTransformer`, which reduces the checks
	performed when visiting nodes.
	"""
	
	def __init__(self, context: libcst.codemod.CodemodContext) -> None:
		libcst.codemod.Codemod.__init__(self, context)
		libcst.CSTTransformer.__init__(self)
	
	def transform_module_impl(self, tree: libcst.Module) -> libcst.Module:
		return tree.visit(self)
	
	def get_leave_funcs(self) -> Mapping[str, _LeaveMethod]:
		"""Return all the valid on_leave methods."""
		methods = inspect.getmembers(
				self,
				lambda m: (inspect.ismethod(m) and m.__name__.startswith("leave_") and not getattr(m, "_is_no_op", False)),
		)
		return dict(methods)
	

class BatchedCodemod(libcst.codemod.Codemod, libcst.CSTTransformer):
	"""Codemod which runs multiple transforms at the same time."""
	
	def __init__(
			self,
			context: libcst.codemod.CodemodContext,
			transformers: Sequence[Type[_ContextAwareTransformer]],
			max_executions: int = 10,
	):
		libcst.codemod.Codemod.__init__(self, context)
		libcst.CSTTransformer.__init__(self)
		self.max_executions = max_executions
		self.leave_methods: MutableMapping[str, List[_LeaveMethod]] = {}
		self.transformers = transformers
		self._batched_transformer: Optional[_BatchedTransformer] = None
	
	def transform_module_impl(self, tree: libcst.Module) -> libcst.Module:
		"""Transform the tree.

		Note: we do not use should_allow_multiple_passes, as that approach
		compares the trees using an expensive deep compare operation. Instead,
		we use the information stored in the context by our transforms.

		This allow us to shave about 10% of the run time.
		"""
		if not self._batched_transformer:
			leave_methods: Dict[str, List[_LeaveMethod]] = {}
			for transform_class in self.transformers:
				for name, method in transform_class(self.context).get_leave_funcs().items():
					leave_methods.setdefault(name.replace("leave_", ""), []).append(method)
			self._batched_transformer = _BatchedTransformer(leave_methods)
			
		self._batched_transformer.update_children_context(self.context)
		
		logger.debug("Checking {}", self.context.filename)
		was_modified = False
		modified_tree = tree
		for _ in range(self.max_executions):
			self._mark_as_not_modified()
			modified_tree = modified_tree.visit(self._batched_transformer)
			if not self._modified():
				break
			was_modified = True
		
		# This is a hack to avoid converting an umodified tree to code. This
		# improves the running time by about 10%.
		if not was_modified:
			raise libcst.codemod.SkipFile()
		logger.debug("Modified {}", self.context.filename)
		return modified_tree
	
	@contextlib.contextmanager
	def _handle_metadata_reference(self, module: libcst.Module) -> Generator[libcst.Module, None, None]:
		"""Optimize the speed of the orginal _handle_metadata_reference.

		Given that we know that CraftierTransform generate always different
		nodes, we can avoid the copy of the whole tree when building the
		metadata. This is an important performance optimization.
		"""
		oldwrapper = self.context.wrapper
		metadata_manager = self.context.metadata_manager
		filename = self.context.filename
		if metadata_manager and filename:
			# We can look up full-repo metadata for this codemod!
			cache = metadata_manager.get_cache_for_path(filename)
			wrapper = libcst.metadata.MetadataWrapper(module, cache=cache, unsafe_skip_copy=True)
		else:
			# We are missing either the repo manager or the current path,
			# which can happen when we are codemodding from stdin or when
			# an upstream dependency manually instantiates us.
			wrapper = libcst.metadata.MetadataWrapper(module, unsafe_skip_copy=True)
		
		with self.resolve(wrapper):
			self.context = dataclasses.replace(self.context, wrapper=wrapper)
			try:
				yield wrapper.module
			finally:
				self.context = dataclasses.replace(self.context, wrapper=oldwrapper)
	
	def _mark_as_not_modified(self) -> None:
		context = self.context.scratch.setdefault(CONTEXT_KEY, {})
		context[self.context.filename] = False
	
	def _modified(self) -> bool:
		context = self.context.scratch.get(CONTEXT_KEY, {})
		return bool(context[self.context.filename])


class _BatchedTransformer(libcst.CSTTransformer):
	def __init__(
			self,
			leave_methods: MutableMapping[str, List[_LeaveMethod]],
	):
		libcst.CSTTransformer.__init__(self)
		self.leave_methods = leave_methods
	
	def on_visit(self, node: libcst.CSTNode) -> bool:
		return True
	
	def on_leave(self, original_node: libcst.CSTNodeT, updated_node: libcst.CSTNodeT) -> Union[libcst.CSTNodeT, libcst.RemovalSentinel]:
		new_updated_node: Union[libcst.CSTNodeT, libcst.RemovalSentinel] = updated_node
		original_node_type = type(original_node)
		for on_leave in self.leave_methods.get(original_node_type.__name__, []):
			# We use type here to detect whether the returned node is still
			# processable by these methods.
			# pylint: disable=unidiomatic-typecheck
			if type(updated_node) != original_node_type:
				break
			new_updated_node = on_leave(original_node, new_updated_node)
			# pylint: enable=unidiomatic-typecheck
		
		return new_updated_node
	
	def on_visit_attribute(self, node: libcst.CSTNode, attribute: str) -> None:
		return None
	
	def on_leave_attribute(self, original_node: libcst.CSTNode, attribute: str) -> None:
		return None
	
	def update_children_context(self, context: libcst.codemod.CodemodContext) -> None:
		"""Propagate the context of the codemod to all children.

		There is some sort of a hack in the LibCST CLI interfaces which change
		the context of an existing codemod, but that does not get propagated all
		the way down.
		"""
		for methods in self.leave_methods.values():
			for method in methods:
				method.__self__.context = context

class CraftierTransformer(_ContextAwareTransformer):
	def _mark_as_modified(self) -> None:
		context = self.context.scratch.setdefault(CONTEXT_KEY, {})
		context[self.context.filename] = True
		


