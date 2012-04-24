# Copyright (c) 2007-2012 PediaPress GmbH
# See README.rst for additional licensing information.

GITVERSIONFILE = mwlib/epub/_gitversion.py
RST2HTML ?= rst2html.py

all:: MANIFEST.in

MANIFEST.in:: 
	./make_manifest.py

README.html: README.rst
	$(RST2HTML) README.rst >README.html

sdist:: all
	@echo gitversion=\"$(shell git describe --tags)\" >$(GITVERSIONFILE)
	@echo gitid=\"$(shell git rev-parse HEAD)\" >>$(GITVERSIONFILE)
	@python setup.py -q build sdist
	@rm -f $(GITVERSIONFILE)*
clean::
	git clean -xfd
	rm -rf build dist README.html
	rm -f $(GITVERSIONFILE)*

pip-install:: clean sdist
	pip uninstall -y mwlib.epub || true
	pip install dist/*

update::
	git pull
	make pip-install
