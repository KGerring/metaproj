#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from __future__ import annotations # isort:skip
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import ast
from pathlib import Path
import pickle

import libcst as cst
from libcst.testing.utils import UnitTest, data_provider
import pytest

from fixit.common.report import AstLintRuleReport, BaseLintRuleReport, CstLintRuleReport


class LintRuleReportTest(UnitTest):
    @data_provider(
        {
            "AstLintRuleReport": [
                AstLintRuleReport(
                    file_path=Path("fake/path.py"),
                    node=ast.parse(""),
                    code="SomeFakeRule",
                    message="some message",
                    line=1,
                    column=1,
                )
            ],
            "CstLintRuleReport": [
                CstLintRuleReport(
                    file_path=Path("fake/path.py"),
                    node=cst.parse_statement("pass\n"),
                    code="SomeFakeRule",
                    message="some message",
                    line=1,
                    column=1,
                    module=cst.MetadataWrapper(cst.parse_module(b"pass\n")),
                    module_bytes=b"pass\n",
                )
            ],
        }
    )
    def test_is_not_pickleable(self, report: BaseLintRuleReport) -> None:
        with pytest.raises(pickle.PicklingError):
            pickle.dumps(report)
