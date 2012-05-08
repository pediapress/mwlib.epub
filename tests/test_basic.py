#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

from mwlib.epub import treeprocessor
from mwlib.epub import collection

def dump_tree(root):
    from lxml import etree
    print etree.tostring(root, pretty_print=True, encoding='utf-8')


def test_safe_xml():
    strings = [('http://blub.com;', 'http___blub_com_'),
               ('(unranked)', '_unranked_')
               ]
    for input, expected_out in strings:
        assert treeprocessor.safe_xml(input) == expected_out

def test_nesting1():
    html='''\
<blockquote>
 <ol>
  <li>blub</li>
 </ol>
 unmotivated text
</blockquote>
'''
    article = collection.article_from_html_frag(html)
    tp = treeprocessor.TreeProcessor()
    tp._fixBareText(article)

    ol = article.tree.xpath('//ol')[0]
    assert ol.tail is None

def test_nesting2():
    html='''\
<blockquote>
 unmotivated text
 <ol>
  <li>blub</li>
 </ol>
</blockquote>
'''
    article = collection.article_from_html_frag(html)
    tp = treeprocessor.TreeProcessor()
    tp._fixBareText(article)

    bq = article.tree.xpath('//blockquote')[0]
    assert bq.text is None
