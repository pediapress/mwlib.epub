#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

import re
from lxml.builder import ElementMaker
from utils.misc import xhtml_page

_ = lambda txt: txt # FIXME: add proper translation support
E = ElementMaker()

def _filterAnonIpEdits(authors):
    if authors:
        authors_text = ', '.join([a for a in authors if a != 'ANONIPEDITS:0'])
        authors_text = re.sub(u'ANONIPEDITS:(?P<num>\d+)', u'\g<num> %s' % _(u'anonymous edits'), authors_text)
    else:
        authors_text = '-'
    return authors_text

def getArticleMetainfo(chapter, collection):
    metainfo = E.ul({'class': 'metainfo'})
    for lvl, webpage in collection.outline.walk():
        if not hasattr(webpage, 'contributors'):
            continue
        contributors = _filterAnonIpEdits(webpage.contributors)
        m = E.li(E.b(webpage.title), ' ',
                 E.i(_('Source')), ': ',
                 E.a(webpage.url, href=webpage.url), ' ',
                 E.i(_('Contributors')), ': ', contributors,
                 )
        metainfo.append(m)

    body_content = [E.h1(_(chapter.title)), metainfo]
    xml = xhtml_page(title=_(chapter.title), body_content=body_content)
    return xml


def getImageMetainfo(chapter, collection):
    metainfo = E.ul({'class': 'metainfo'})
    for img_title, info in collection.img_contributors.items():
        contributors = _filterAnonIpEdits(info['contributors'])
        m = E.li(E.b(img_title), ' ',
                 E.i(_('Source')), ': ',
                 E.a(info['url'], href=info['url']), ' ',
                 E.i(_('License')), ': ', info['license'], ' ',
                 E.i(_('Contributors')), ': ', contributors,
                 )
        metainfo.append(m)
    body_content = [E.h1(_(chapter.title)), metainfo]
    xml = xhtml_page(title=_(chapter.title), body_content=body_content)
    return xml
