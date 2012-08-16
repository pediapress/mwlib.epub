#! /usr/bin/env python

# Copyright (c) 2011 PediaPress GmbH
# See README.txt for additional licensing information.

import sys, os

if not (2, 5) < sys.version_info[:2] < (3, 0):
    sys.exit("""
***** ERROR ***********************************************************
* mwlib.epub does not work with python %s.%s. You need to use python 2.6
* or 2.7
***********************************************************************
""" % sys.version_info[:2])


from setuptools import setup, Extension


def get_version():
    d = {}
    execfile( 'mwlib/epub/_version.py', d, d)
    return d["version"]

install_requires = ['mwlib', 'lxml', 'cssutils', 'ordereddict']


def main():
    if os.path.exists('Makefile'):
        print 'Running make'
        os.system('make')
    setup(
        name="mwlib.epub",
        version=get_version(),
        entry_points={'mwlib.writers': ['epub = mwlib.epub.epubwriter:writer']},
        install_requires=install_requires,
        packages=["mwlib", "mwlib.epub"],
        namespace_packages=['mwlib'],
        zip_safe=False,
        include_package_data=True,
        url="http://code.pediapress.com/",
        description="generate epub files from mediawiki markup",
        long_description=open("README.rst").read(),
        license="BSD License",
        maintainer="pediapress.com",
        maintainer_email="info@pediapress.com")

if __name__ == '__main__':
    main()
