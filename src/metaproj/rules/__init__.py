#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from __future__ import annotations # isort:skip
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import annotations

from fixit.common.utils import import_to_namespace

rules = {}
import_to_namespace(locals(), __name__, __path__)
