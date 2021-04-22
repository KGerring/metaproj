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

__all__ = []

import sys
import os

__all__ = sorted(
		[getattr(v, '__name__', k)
		 for k, v in list(globals().items())  # export
		 if ((callable(v) and getattr(v, "__module__", "") == __name__  # callables from this module
		      or k.isupper()) and  # or CONSTANTS
		     not str(getattr(v, '__name__', k)).startswith('__'))]
)  # neither marked internal

if __name__ == '__main__':
	print(__file__)
