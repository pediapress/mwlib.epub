#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

import pytest
from lxml import etree

from mwlib.epub import treeprocessor
from mwlib.epub import collection

def dump_tree(root):
    print etree.tostring(root, pretty_print=True, encoding='utf-8')

def get_tidy_tree(html, dump=False):
    html = etree.tostring(etree.HTML(html), encoding='utf-8')
    html, errors = collection.tidy_xhtml(html)
    if dump:
        print '>'*40
        print html
        if errors:
            print '!'*40
            print errors
    return etree.HTML(html)

def test_safe_xml():
    strings = [('http://blub.com;', 'http___blub_com_'),
               ('(unranked)', '_unranked_')
               ]
    for input, expected_out in strings:
        assert treeprocessor.safe_xml(input) == expected_out

def test_bare_text_trivial():
    html = '''\
<blockquote>
 unmotivated text
</blockquote>
    '''
    tree = get_tidy_tree(html)
    bq = tree.xpath('//blockquote')[0]
    assert len(bq.text.strip()) == 0

@pytest.mark.xfail
def test_bare_text_simple():
    html='''\
<blockquote>
 <ol>
  <li>blub</li>
 </ol>
 unmotivated text
</blockquote>
'''
    tree = get_tidy_tree(html)
    ol = tree.xpath('//ol')[0]
    dump_tree(tree)
    assert ol.tail is None
