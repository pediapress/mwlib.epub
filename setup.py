#! /usr/bin/env python

# Copyright (c) 2011 PediaPress GmbH
# See README.txt for additional licensing information.

import os
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
