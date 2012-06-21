#! /usr/bin/env python

# Copyright (c) 2011 PediaPress GmbH
# See README.txt for additional licensing information.

import os

try:
    from setuptools import setup, Extension
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, Extension

version=None
execfile('mwlib/epub/_version.py')
# adds 'version' to local namespace

install_requires=['mwlib', 'lxml', 'cssutils']

def read_long_description():
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.rst")
    return open(fn).read()

def main():
    if os.path.exists('Makefile'):
        print 'Running make'
        os.system('make')
    setup(
        name="mwlib.epub",
        version=str(version),
        entry_points = {
            'mwlib.writers': ['epub = mwlib.epub.epubwriter:writer'],
        },
        install_requires=install_requires,
        packages=["mwlib", "mwlib.epub"],
        namespace_packages=['mwlib'],
        zip_safe=False,
        include_package_data=True,
        url = "http://code.pediapress.com/",
        description="generate epub files from mediawiki markup",
        long_description = read_long_description(),
        license="BSD License",
        maintainer="pediapress.com",
        maintainer_email="info@pediapress.com",
    )

if __name__ == '__main__':
    main()
