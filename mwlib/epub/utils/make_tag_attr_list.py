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
    tag2required = {}
    repl_map = {'common': ['xml:space', 'class', 'id', 'title', 'dir', 'xml:lang', 'style'],
                'core': ['xml:space', 'class', 'id', 'title'],
                'i18n': ['dir', 'xml:lang'],
                }

    content_repl = dict(Heading=['h1', 'h2', 'h3', 'h4', 'h5', 'h6',],
                        Block=['address', 'blockquote', 'div', 'p', 'pre', 'hr', 'table','noscript',],
                        Inline=['abb', 'acronym', 'br', 'cite', 'code', 'dfn', 'em', 'kbd',
                                'q', 'samp', 'span', 'strong', 'var', 'a', 'b', 'big', 'i',
                                'small', 'sub', 'sup', 'tt', 'del', 'ins', 'bdo', 'img', 'map',
                                'object', 'noscript',
                                ],
                        Form=['form', 'fieldset'],
                        Formctrl=['input', 'label', 'select', 'textarea', 'button'],
                        List=['dl', 'ol', 'ul',],
                        )

    content_repl['Flow'] = content_repl['Heading'] + content_repl['Block'] + \
                           content_repl['Inline'] + content_repl['List']

    allowed_tags = {}
    empty_ok = []

    for row in html.xpath('//table//tbody//tr'):
        module = row.xpath('./preceding::h3|./preceding::h2')
        if module:
            module_name = module[-1].text.split(' ', 1)[-1]

        node_name = row.xpath('./td[position()=1]')[0].text
        if not node_name or '&' in node_name or module_name == 'Legacy Module':
            continue

        print '*'*40, node_name

        # build allowed attributes
        attributes = ''.join(x for x in row.xpath('./td[position()=2]')[0].itertext())
        #attributes = re.sub('\(.*?\)|\*', '', attributes.replace('\n', ''))
        attributes = re.sub('\(.*?\)', '', attributes.replace('\n', ''))
        attributes = set(x.strip().lower() for x in re.split(',| ', attributes) if x)
        required_attributes = [attr[:-1] for attr in attributes if attr.endswith('*')]
        attributes = set([attr[:-1] if attr.endswith('*') else attr for attr in attributes])

        for abbrev, full in repl_map.items():
            if abbrev in attributes:
                attributes.remove(abbrev)
                attributes.update(full)
        tag2attrs[node_name] = list(attributes)
        if required_attributes:
            tag2required[node_name] = required_attributes

        # build minimal content model
        content = ''.join(x for x in row.xpath('./td[position()=3]')[0].itertext())
        print content

        if ('*' in content and '+' not in content) or content in ['EMPTY', 'PCDATA']:
            empty_ok.append(node_name)

        content = re.sub('\(|\)|\*|\+|\?|\||\,|\-', '', content.replace('\n', ''))
        content = set(x.strip() for x in re.split(' ', content) if x)
        if node_name in content:
            content.remove(node_name)
        for abbrev, full in content_repl.items():
            if abbrev in content:
                content.remove(abbrev)
                content.update(full)

        allowed_tags[node_name] = list(content)

    #FIXME: add meta, to html
    # add script, style, link, base, to head

    allowed_tags['article'] = ['head', 'body', 'div']
    allowed_tags['html'].append('meta')
    allowed_tags['head'].extend(['script', 'style', 'link', 'base'])

    open('tag2attr.json', 'w').write(json.dumps(tag2attrs, indent=4))
    json.dump(allowed_tags, open('allowed_tags.json', 'w'), indent=4)
    json.dump(empty_ok, open('empty_ok.json', 'w'), indent=4)

def doit():
    html = fetch(url='http://www.w3.org/TR/xhtml-modularization/abstract_modules.html')
    parseW3C(html)

if __name__ == '__main__':
    doit()
