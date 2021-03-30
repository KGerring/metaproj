#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from __future__ import unicode_literals

import doctest
import os
import sys

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.extlinks",
    "sphinx.ext.ifconfig",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
]
if os.getenv("SPELLCHECK"):
    extensions += ("sphinxcontrib.spelling",)
    spelling_show_suggestions = True
    spelling_lang = "en_US"

try:
    import sphinxcontrib.inspection_tags

    extensions.append("sphinxcontrib.inspection_tags")
    tasklist_all_tasknotes = True

except Exception:
    pass
source_suffix = ".rst"
master_doc = "index"
project = "metaproj"
year = "<YEAR>"
author = "KGerring"
copyright = "{0}, {1}".format(year, author)
version = release = "0.1.0"

default_role = "literal"
pygments_style = "sphinx"
highlight_language = "python3"
add_function_parentheses = False

templates_path = ["_templates"]
html_static_path = ["_static"]
extlinks = {
    "issue": ("https://github.com/KGerring/metaproj/issues/%s", "#"),
    "pr": ("https://github.com/KGerring/metaproj/pull/%s", "PR #"),
}
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get("READTHEDOCS", None) == "True"

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = "sphinx_rtd_theme"

html_show_copyright = False
html_show_sphinx = False
html_use_smartypants = False
html_last_updated_fmt = "%b %d, %Y"
html_split_index = False
html_domain_indices = True
html_use_index = True
html_use_modindex = True
html_sidebars = {
    "**": ["searchbox.html", "globaltoc.html", "sourcelink.html"],
}
html_short_title = "%s-%s" % (project, version)


manpages_url = "https://manpages.debian.org/{path}"
todo_include_todos = True

trim_doctests_flags = True
DOCTEST_OPTIONFLAGS = doctest.OPTIONFLAGS_BY_NAME
DOCTEST_FLAGS = (
    "ELLIPSIS",
    "IGNORE_EXCEPTION_DETAIL",
    "NORMALIZE_WHITESPACE",
    "REPORT_UDIFF",
    "SKIP",
)

doctest_default_flags = sum([DOCTEST_OPTIONFLAGS.get(f) for f in DOCTEST_FLAGS if f])
autodoc_member_order = "bysource"
autodoc_default_options = {"noindex": True, "member-order": "bysource"}
autodoc_default_flags = ["noindex"]

INTERSPHINX_MAPPING = [
    ("python", ("https://docs.python.org/dev/", None)),
    ("sphinx", ("https://www.sphinx-doc.org/en/stable/", None)),
    ("redis", ("https://redis-py.readthedocs.io/en/latest/", None)),
    ("pytest", ("https://doc.pytest.org/en/latest/", None)),
    ("tox", ("https://tox.readthedocs.io/en/latest", None)),
]

intersphinx_mapping = dict(INTERSPHINX_MAPPING)


napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False
