#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

from lxml.builder import ElementMaker
from lxml import etree

E = ElementMaker()

def get_css_link_element():
    return E.link(rel='stylesheet',
                  href='wp.css',
                  type='text/css')


def flatten_tree(tree):
    return etree.tostring(tree,
                          pretty_print=True,
                          encoding='utf-8',
                          xml_declaration=True,
                          method='xml',
                          doctype='<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'
                          )


def xhtml_page(title='', body_content=None, flatten=True):
    head = E.head(
        E.meta({'http-equiv':"Content-Type",
                'content': "application/xhtml+xml; charset=utf-8"}),
        E.title(title),
        get_css_link_element(),
        )
    # add styles in case
    body = E.body()
    tree = E.html({'xmlns':'http://www.w3.org/1999/xhtml'},
                  head,
                  body,
                  )

    for element in body_content:
        body.append(element)

    if flatten:
        return flatten_tree(tree)
    else:
        return tree
