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

def show(root):
    #print etree.tostring(root, pretty_print=True, encoding='utf-8')
    print etree.tostring(root, pretty_print=True)

def test_safe_xml():
    strings = [('http://blub.com;', 'http___blub_com_'),
               ('(unranked)', '_unranked_')
               ]
    for input, expected_out in strings:
        assert treeprocessor.safe_xml(input) == expected_out


def test_remove_references_1(tmpdir):
    frag = '''\
bla1<sup id="cite_ref-0" class="reference"><a href="#cite_note-0"><span>[</span>1<span>]</span></a></sup>

<h2><span class="editsection">[<a href="/w/index.php?title=1994_Atlantic_hurricane_season&amp;action=edit&amp;section=11" title="Edit section: References">edit</a>]</span> <span class="mw-headline" id="References">References</span></h2>
<div class="reflist references-column-width" style="-moz-column-width: 30em; -webkit-column-width: 30em; column-width: 30em; list-style-type: decimal;">
<ol class="references">
<li id="cite_note-0"><span class="mw-cite-backlink">blub</li>
<li id="cite_note-HURDAT-1"><span class="mw-cite-backlink">blub</li>
</ol>
</div>

bla2

<h2>noremove</h2>
<p>bla3</p>
    '''

    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'references1.epub')
    tree = etree.HTML(xhtml)
    show(tree)

    assert not tree.xpath('//sup[contains(@id, "cite_ref")]')
    assert not tree.xpath('//li[contains(@id, "cite_note")]')
    assert not tree.xpath('//span[@id="References"]')
    assert tree.xpath('//h2[text()="noremove"]')

def test_remove_references_2(tmpdir):
    frag = '''\
<h2>noremove</h2>
<div class="sisterproject" style="margin:0.1em 0 0 0;"><img alt="" src="//upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Commons-logo.svg/12px-Commons-logo.svg.png" height="16" width="12">&nbsp;<b><span class="plainlinks"><a class="external text" href="//commons.wikimedia.org/wiki/Category:Freital?uselang=de">Commons: Freital</a></span></b>&nbsp;– Sammlung von Bildern, Videos und Audiodateien</div>
<ul><li> <a rel="nofollow" class="external text" href="http://www.freital.de/">Website der Stadt Freital</a>
</li><li> <a rel="nofollow" class="external text" href="http://hov.isgv.de/Freital">Freital</a> im <i>Digitalen Historischen Ortsverzeichnis von Sachsen</i>
</li></ul>
<h2><span class="mw-headline" id="Einzelnachweise"> Einzelnachweise </span> <span class="editsection">[<a href="/w/index.php?title=Freital&amp;action=edit&amp;section=36" title="Abschnitt bearbeiten: Einzelnachweise">Bearbeiten</a>]</span></h2>
<ol class="references"><li id="cite_note-Metadaten_Einwohnerzahl_DE-SN-0"><span class="mw-cite-backlink"><a href="#cite_ref-Metadaten_Einwohnerzahl_DE-SN_0-0">↑</a></span> <span class="reference-text"><a rel="nofollow" class="external text" href="http://www.statistik.sachsen.de/download/010_GB-Bev/Bev_Gemeinde.pdf">Statistisches Landesamt des Freistaates Sachsen – Bevölkerung des Freistaates Sachsen jeweils am Monatsende ausgewählter Berichtsmonate nach Gemeinden</a>&nbsp;(<a href="/wiki/Wikipedia:WikiProjekt_Kommunen_und_Landkreise_in_Deutschland/Einwohnerzahlen" title="Wikipedia:WikiProjekt Kommunen und Landkreise in Deutschland/Einwohnerzahlen">Hilfe dazu</a>)</span>
</li>
<li id="cite_note-LEP2003-1"><span class="mw-cite-backlink">↑ <sup><a href="#cite_ref-LEP2003_1-0">a</a></sup> <sup><a href="#cite_ref-LEP2003_1-1">b</a></sup></span> <span class="reference-text"><span class="Z3988" title="ctx_ver=Z39.88-2004&amp;rft_val_fmt=info%3Aofi%2Ffmt%3Akev%3Amtx%3Abook&amp;rfr_id=info%3Asid%2Fde.wikipedia.org%3AFreital&amp;rft.genre=book&amp;rft.btitle=Landesentwicklungsplan+Sachsen+2003&amp;rft.au=Freistaat+Sachsen%2C+Staatsministerium+des+Innern+%28Hrsg.%29"><span style="display: none;">&nbsp;</span></span>Freistaat Sachsen, Staatsministerium des Innern (Hrsg.): <i>Landesentwicklungsplan Sachsen 2003</i>. (<a rel="nofollow" class="external text" href="http://www.landesentwicklung.sachsen.de/2387.htm">Landesentwicklungsplan 2003</a>).</span>
</li>
<li id="cite_note-GSS11-2"><span class="mw-cite-backlink">↑ <sup><a href="#cite_ref-GSS11_2-0">a</a></sup> <sup><a href="#cite_ref-GSS11_2-1">b</a></sup> <sup><a href="#cite_ref-GSS11_2-2">c</a></sup> <sup><a href="#cite_ref-GSS11_2-3">d</a></sup> <sup><a href="#cite_ref-GSS11_2-4">e</a></sup> <sup><a href="#cite_ref-GSS11_2-5">f</a></sup> <sup><a href="#cite_ref-GSS11_2-6">g</a></sup> <sup><a href="#cite_ref-GSS11_2-7">h</a></sup></span></li>
</ol>
    '''

    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'references2.epub')
    tree = etree.HTML(xhtml)
    show(tree)

    assert not tree.xpath('//sup[contains(@id, "cite_ref")]')
    assert not tree.xpath('//li[contains(@id, "cite_note")]')
    assert not tree.xpath('//span[@id="Einzelnachweise"]')
    assert tree.xpath('//h2[text()="noremove"]')


def test_convert_center(tmpdir):
    frag='''\
<center>
this is centered text
</center>
'''
    xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'convert_center.epub')
    tree = etree.HTML(xhtml)
    show(tree)
    assert len(tree.xpath('//center')) == 0
    assert ''.join(tree.xpath('//div')[0].itertext()).strip() == 'this is centered text'
