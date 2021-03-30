# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile


SPHINXAUTOBUILD = sphinx-autobuild
# -B `open browser` , then srcdir outdir [filenames] at end

ALLSPHINXLIVEOPTS   = $(SPHINXOPTS) -q \
	-p 0 \
	-H 0.0.0.0 \
	-B \
   --delay 1 \
   --ignore "*.swp" \
   --ignore "*.pdf" \
   --ignore "*.log" \
   --ignore "*.out" \
   --ignore "*.toc" \
   --watch source

LIVEOPTS = -B --delay 1

# you can add multiple `--watch dir` flags (`-z dir` for shorthand)

.PHONY: livehtml
livehtml:
	$(SPHINXAUTOBUILD) -b html $(ALLSPHINXLIVEOPTS) $(BUILDDIR)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)." 

.PHONY: autobuild
autobuild:
	$(SPHINXAUTOBUILD)  $(LIVEOPTS) $(SOURCEDIR)  $(BUILDDIR)
	@echo
	@echo "sphinx-autobuild started for  $(SOURCEDIR) ."


# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
