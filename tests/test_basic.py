#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

import subprocess

import pytest
from lxml import etree

from mwlib.epub import treeprocessor
from mwlib.epub import collection
from mwlib.epub import epubwriter

def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return p.returncode, stdout, stderr

def render_frag(frag, tmpdir, epub_fn):
    full_fn = str(tmpdir.join(epub_fn))
    xhtml = epubwriter.render_fragment(full_fn, frag, dump_xhtml=True)
    ret, stdout, stderr = run_cmd(['epubcheck',
                           full_fn])
    return xhtml, ret, stdout, stderr

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

def test_convert_center():
    html='''\
<center>
this is centered text
</center>
'''
    tree = get_tidy_tree(html)
    assert len(tree.xpath('//center')) == 0

def test_tidy_old_tags(tmpdir):
    frag = '''\
<center>
this is centered text
</center>
'''
    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'tidy_old_tags.epub')
    assert ret == 0

def test_tidy_ids(tmpdir):
    frag = '''\
    <p id="blub17:42">bla</p>
'''

    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'tidy_ids.epub')
    assert ret == 0

def test_ref_link(tmpdir):
    frag = '''\
<p>blub<sup id="cite_ref-0" class="reference"><a href="#cite_note-0">[1]</a></sup></p>
<ol class="references">
<li id="cite_note-0"><span class="mw-cite-backlink"><a href="#cite_ref-0">up</a></span> <span class="reference-text">bla</span></li>
</ol>

'''

    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'ref_links.epub')
    tree = etree.HTML(xhtml)
    a =tree.xpath('//a')[0]
    assert a.get('id') == None
