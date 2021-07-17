#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = cst_utc
# author=KGerring
# date = 6/15/21
# project poetryproj
# docs root 
"""
 poetryproj  

"""

__all__ = []

import sys  # isort:skip
import os  # isort:skip
import re  # isort:skip
from typing import cast

import libcst as cst
import libcst.matchers as m
from libcst.codemod import VisitorBasedCodemodCommand
from libcst.codemod.visitors import (
	AddImportsVisitor,
	RemoveImportsVisitor,
)


class DatetimeUtcnow_(VisitorBasedCodemodCommand):
	
	DESCRIPTION: str = "Converts from datetime.utcnow() to datetime.utc()"
	
	timezone_utc_matcher = m.Arg(
			value=m.Attribute(
					value=m.Name(value="timezone"), attr=m.Name(value="utc")
			),
			keyword=m.Name(value="tzinfo"),
	)
	
	utc_matcher = m.Arg(
			value=m.OneOf(
					m.Name(value="utc"),
					m.Name(value="UTC"),
					m.Attribute(value=m.Name(value="pytz",), attr=m.Name(value="UTC")),
			),
			keyword=m.Name(value="tzinfo"),
	)
	
	datetime_utcnow_matcher = m.Call(
			func=m.Attribute(
					value=m.Name(value="datetime"), attr=m.Name(value="utcnow")
			),
			args=[],
	)
	datetime_datetime_utcnow_matcher = m.Call(
			func=m.Attribute(
					value=m.Attribute(
							value=m.Name(value="datetime"), attr=m.Name(value="datetime")
					),
					attr=m.Name(value="utcnow"),
			),
			args=[],
	)
	
	datetime_replace_matcher = m.Call(
			func=m.Attribute(
					value=datetime_utcnow_matcher, attr=m.Name(value="replace")
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	datetime_datetime_replace_matcher = m.Call(
			func=m.Attribute(
					value=datetime_datetime_utcnow_matcher,
					attr=m.Name(value="replace"),
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	
	timedelta_replace_matcher = m.Call(
			func=m.Attribute(
					value=m.BinaryOperation(
							left=m.OneOf(
									datetime_utcnow_matcher, datetime_datetime_utcnow_matcher
							),
							operator=m.Add(),
					),
					attr=m.Name(value="replace"),
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	
	utc_localize_matcher = m.Call(
			func=m.Attribute(
					value=m.Name(value="UTC"), attr=m.Name(value="localize"),
			),
			args=[
					m.Arg(
							value=m.OneOf(
									datetime_utcnow_matcher, datetime_datetime_utcnow_matcher
							)
					)
			],
	)
	
	def _update_imports(self):
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz")
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz", "utc")
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz", "UTC")
		RemoveImportsVisitor.remove_unused_import(
				self.context, "datetime", "timezone"
		)
		AddImportsVisitor.add_needed_import(
				self.context, "bulb.platform.common.timezones", "UTC"
		)
	
	@m.leave(datetime_utcnow_matcher)
	def datetime_utcnow_call(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Name(value="datetime"), attr=cst.Name("now")
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_datetime_utcnow_matcher)
	def datetime_datetime_utcnow_call(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Attribute(
								value=cst.Name(value="datetime"),
								attr=cst.Name(value="datetime"),
						),
						attr=cst.Name(value="now"),
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_replace_matcher)
	def datetime_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Name(value="datetime"), attr=cst.Name("now")
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_datetime_replace_matcher)
	def datetime_datetime_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Attribute(
								value=cst.Name(value="datetime"),
								attr=cst.Name(value="datetime"),
						),
						attr=cst.Name(value="now"),
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(timedelta_replace_matcher)
	def timedelta_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.BinaryOperation:
		self._update_imports()
		
		return cast(
				cst.BinaryOperation,
				cast(cst.Attribute, cast(cst.Call, updated_node).func).value,
		)
	
	@m.leave(utc_localize_matcher)
	def utc_localize(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return cast(cst.Call, updated_node.args[0].value)


class DatetimeUtcnow(VisitorBasedCodemodCommand):
	
	DESCRIPTION: str = "Converts from datetime.utcnow() to datetime.utc()"
	
	timezone_utc_matcher = m.Arg(
			value=m.Attribute(
					value=m.Name(value="timezone"), attr=m.Name(value="utc")
			),
			keyword=m.Name(value="tzinfo"),
	)
	
	utc_matcher = m.Arg(
			value=m.OneOf(
					m.Name(value="utc"),
					m.Name(value="UTC"),
					m.Attribute(value=m.Name(value="pytz", ), attr=m.Name(value="UTC")),
			),
			keyword=m.Name(value="tzinfo"),
	)
	
	datetime_utcnow_matcher = m.Call( #datetime.utcnow()
			func=m.Attribute(
					value=m.Name(value="datetime"), attr=m.Name(value="utcnow")
			),
			args=[],
	)
	datetime_datetime_utcnow_matcher = m.Call( #datetime.datetime.utcnow()
			func=m.Attribute(
					value=m.Attribute(
							value=m.Name(value="datetime"), attr=m.Name(value="datetime")
					),
					attr=m.Name(value="utcnow"),
			),
			args=[],
	)
	
	datetime_replace_matcher = m.Call(
			func=m.Attribute(
					value=datetime_utcnow_matcher, attr=m.Name(value="replace")
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	datetime_datetime_replace_matcher = m.Call(
			func=m.Attribute(
					value=datetime_datetime_utcnow_matcher,
					attr=m.Name(value="replace"),
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	
	timedelta_replace_matcher = m.Call(
			func=m.Attribute(
					value=m.BinaryOperation(
							left=m.OneOf(
									datetime_utcnow_matcher, datetime_datetime_utcnow_matcher
							),
							operator=m.Add(),
					),
					attr=m.Name(value="replace"),
			),
			args=[m.OneOf(timezone_utc_matcher, utc_matcher)],
	)
	
	utc_localize_matcher = m.Call(
			func=m.Attribute(
					value=m.Name(value="UTC"), attr=m.Name(value="localize"),
			),
			args=[
					m.Arg(
							value=m.OneOf(
									datetime_utcnow_matcher, datetime_datetime_utcnow_matcher
							)
					)
			],
	)
	
	def _update_imports(self):
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz")
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz", "utc")
		RemoveImportsVisitor.remove_unused_import(self.context, "pytz", "UTC")
		RemoveImportsVisitor.remove_unused_import(
				self.context, "datetime", "timezone"
		)
		AddImportsVisitor.add_needed_import(
				self.context, "bulb.platform.common.timezones", "UTC"
		)
	
	@m.leave(datetime_utcnow_matcher)
	def datetime_utcnow_call(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Name(value="datetime"), attr=cst.Name("now")
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_datetime_utcnow_matcher)
	def datetime_datetime_utcnow_call(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Attribute(
								value=cst.Name(value="datetime"),
								attr=cst.Name(value="datetime"),
						),
						attr=cst.Name(value="now"),
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_replace_matcher)
	def datetime_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Name(value="datetime"), attr=cst.Name("now")
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(datetime_datetime_replace_matcher)
	def datetime_datetime_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return updated_node.with_changes(
				func=cst.Attribute(
						value=cst.Attribute(
								value=cst.Name(value="datetime"),
								attr=cst.Name(value="datetime"),
						),
						attr=cst.Name(value="now"),
				),
				args=[cst.Arg(value=cst.Name(value="UTC"))],
		)
	
	@m.leave(timedelta_replace_matcher)
	def timedelta_replace(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.BinaryOperation:
		self._update_imports()
		
		return cast(
				cst.BinaryOperation,
				cast(cst.Attribute, cast(cst.Call, updated_node).func).value,
		)
	
	@m.leave(utc_localize_matcher)
	def utc_localize(
			self, original_node: cst.Call, updated_node: cst.Call
	) -> cst.Call:
		self._update_imports()
		
		return cast(cst.Call, updated_node.args[0].value)




if __name__ == '__main__':
	print(__file__)
