#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import os
import urllib
import json
import re
from lxml import etree

def fetch(url):
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


def parseW3C(html):
    tag2attrs = {}
    repl_map = {'common': ['xml:space', 'class', 'id', 'title', 'dir', 'xml:lang', 'style'],
                'core': ['xml:space', 'class', 'id', 'title'],
                'i18n': ['dir', 'xml:lang'],
                }

    for row in html.xpath('//table//tbody//tr'):
        # module = row.xpath('./preceding::h3|./preceding::h2')
        # if module:
        #     module_name = module[-1].text.split(' ', 1)[-1]

        node_name = row.xpath('./td[position()=1]')[0].text
        if not node_name or '&' in node_name:
            continue
        attributes = ''.join(x for x in row.xpath('./td[position()=2]')[0].itertext())
        attributes = re.sub('\(.*?\)|\*', '', attributes.replace('\n', ''))
        attributes = set(x.strip().lower() for x in re.split(',| ', attributes) if x)
        for abbrev, full in repl_map.items():
            if abbrev in attributes:
                attributes.remove(abbrev)
                attributes.update(full)
        tag2attrs[node_name] = list(attributes)

    open('tag2attr.json', 'w').write(json.dumps(tag2attrs, indent=4))

def doit():
    html = fetch(url='http://www.w3.org/TR/xhtml-modularization/abstract_modules.html')
    parseW3C(html)

if __name__ == '__main__':
    doit()
