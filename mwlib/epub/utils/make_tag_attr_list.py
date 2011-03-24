#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import os
import urllib
import json
from lxml import etree

def fetch(url='http://www.webpelican.com/web-tutorials/xhtml-1-1-tutorial/'):
    data_fn = 'data.html'

    if not os.path.exists(data_fn):
        data = urllib.urlopen(url).read()
        print 'fetching data'
        f = open(data_fn, 'w')
        f.write(data)
        f.close()
    else:
        data = open(data_fn).read()
    print 'got data'
    return etree.HTML(data)

def fix(tag2attrs):
    td = tag2attrs['td']
    td.append('class')
    tag2attrs['td'] = td

def parse(html):
    tag2attrs = {}
    tables = html.xpath('//table')
    for table in tables:
        if any(ancestor.tag == 'table' for ancestor in table.iterancestors()):
            continue
        for row in table.xpath('./tbody/tr'):
            tags = row.xpath('./td[position()=1]/text()')
            attrs = row.xpath('./td[position()=2]/text()')
            if tags and attrs:
                for tag in tags:
                    tag = tag.replace('<', '').replace('>', '').replace('/', '').strip()
                    attrs = [attr.replace(' ', '').strip() for attr in attrs]
                    tag2attrs[tag]=attrs
    fix(tag2attrs)
    open('tag2attr.json', 'w').write(json.dumps(tag2attrs))

def doit():
    html = fetch()
    parse(html)

if __name__ == '__main__':
    doit()
