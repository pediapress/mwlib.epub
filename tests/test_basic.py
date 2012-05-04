#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

from mwlib.epub import treeprocessor


def test_safe_xml():
    strings = [('http://blub.com;', 'http___blub_com_'),
               ('(unranked)', '_unranked_')
               ]
    for input, expected_out in strings:
        assert treeprocessor.safe_xml(input) == expected_out
