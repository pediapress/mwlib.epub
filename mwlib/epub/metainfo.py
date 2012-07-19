#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

import re

from xml.sax.saxutils import escape as xmlescape

from lxml import etree
from lxml.builder import ElementMaker

_ = lambda txt: txt # FIXME: add proper translation support
E = ElementMaker()

metainfo_skeleton = '''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>%(title)s</title></head>
<body><h1 style="margin-top:15%%;font-size:300%%;text-align:center;">%(title)s</h1>

%(metainfo)s

</body>
</html>
'''

def _filterAnonIpEdits(authors):
    if authors:
        authors_text = ', '.join([a for a in authors if a != 'ANONIPEDITS:0'])
        authors_text = re.sub(u'ANONIPEDITS:(?P<num>\d+)', u'\g<num> %s' % _(u'anonymous edits'), authors_text)
    else:
        authors_text = '-'
    return authors_text

def getArticleMetainfo(chapter, collection):
    metainfo = E.ul(style='list-style-type:none;font-size:75%')
    for lvl, webpage in collection.outline.walk():
        contributors = _filterAnonIpEdits(webpage.contributors)
        m = E.li(E.b(webpage.title), ' ',
                 E.i(_('Source')), ': ', webpage.url, ' ',
                 E.i(_('Contributors')), ': ', contributors,
                 style='margin-bottom:1em;'
                 )
        metainfo.append(m)

    xml = metainfo_skeleton % dict(title=xmlescape(_(chapter.title)),
                                   metainfo=etree.tostring(metainfo))
    return xml
