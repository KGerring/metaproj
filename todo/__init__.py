#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename = __init__
# author=KGerring
# date = 4/15/21
# project poetryproj
# docs root
"""
 poetryproj  

"""
from __future__ import annotations

import os
import sys

__all__ = []


__all__ = sorted(
    [
        getattr(v, "__name__", k)
        for k, v in list(globals().items())  # export
        if (
            (callable(v) and getattr(v, "__module__", "") == __name__ or k.isupper())  # callables from this module
            and not str(getattr(v, "__name__", k)).startswith("__")  # or CONSTANTS
        )
    ]
)  # neither marked internal

if __name__ == "__main__":
    print(__file__)
