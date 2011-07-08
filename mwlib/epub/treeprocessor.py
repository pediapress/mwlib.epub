#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import os
from StringIO import StringIO
import urlparse
import urllib
import re
import json
from lxml import etree

# Source of list: http://idpf.org/epub/20/spec/OPS_2.0.1_draft.htm#Section2.2.1
allowed_tags = 'body, head, html, title, abbr, acronym, address, blockquote, br, cite, code, dfn, div, em, h1, h2, h3, h4, h5, h6, kbd, p, pre, q, samp, span, strong, var, a, dl, dt, dd, ol, ul, li, object, param, b, big, hr, i, small, sub, sup, tt, del, ins, bdo, caption, col, colgroup, table, tbody, td, tfoot, th, thead, tr, img, area, map, meta, style, link, base'.split(', ')

def safe_xml(txt, mode='id'):
    txt = txt.replace(':', '_').replace('.', '_').replace('/', '_').replace(';', '_')
    if mode == 'id':
        txt = re.sub('(\d)', lambda n: chr(97 + int(n.groups()[0])), txt)
    return txt

def safe_xml_id(txt):
    return safe_xml(txt, mode='id')

def clean_url(url):
    return urlparse.urlunsplit([urllib.quote(urllib.unquote(frag), safe='/=&+')
                                for frag in urlparse.urlsplit(url.encode('utf-8'))]).decode('utf-8')

def remove_node(node):
    '''remove node but keep tail if present'''

    parent = node.getparent()
    assert len(parent)
    if not node.tail:
        parent.remove(node)
        return
    prev = node.getprevious()
    if prev is not None:
        if prev.tail:
            prev.tail += node.tail
        else:
            prev.tail = node.tail
        parent.remove(node)
        return
    parent.text = parent.text or ''
    parent.text += node.tail
    parent.remove(node)

class CleanerException(Exception):
    pass

class TreeProcessor(object):

    xslt_head = '<xsl:transform version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">'
    xslt_foot = '''
 <xsl:template match="node()|@*">
  <xsl:copy>
   <xsl:apply-templates select="node()|@*"/>
  </xsl:copy>
 </xsl:template>
</xsl:transform>'''

    def __init__(self):
        pass


    def _setTitle(self, article):
        title_node = article.tree.find('.//title')
        if not title_node:
            title_node = etree.Element('title')
        title_node.text = article.title
        head_node = article.tree.find('.//head')
        head_node.append(title_node)


    def annotateNodes(self, article):
        self._setTitle(article)

    def clean(self, article):
        self.sanitize(article)
        self.mapTags(article)
        self.transformNodes(article)
        self.removeNodes(article)
        self.moveNodes(article)
        self.applyXSLT(article)
        self.improveLayout(article)
        self.removeInvisible(article)
        self.clearStyles(article)
        self.makeValidXhtml(article)


    def _centerImages(self, article):
        for node in article.tree.xpath('//*[contains(@style, text-align)]//img[not(@align)]'):
            node.set('align', 'center')


    def improveLayout(self, article):
        self._centerImages(article)

    def clearStyles(self, article):
        clear_font_size = re.compile('font-size *:.*?(;|$)')
        clear_table_width = re.compile('width *:.*?(;|$)')

        for node in article.tree.xpath('//*[@style]'):
            style = node.get('style')
            new_style = re.sub(clear_font_size, '', style)
            if new_style != style:
                node.set('style', new_style)

            # FIXME: hack to allow full width image captions
            if node.get('class') == 'thumbinner' and node.get('style'):
                del node.attrib['style']

            if node.tag == 'table' and node.get('style'):
                style = node.get('style')
                no_width = re.sub(clear_table_width, '', style)
                if no_width != style:
                    node.set('style', no_width)


    def removeInvisible(self, article):
        delete = []
        for node in article.tree.iter():
            style = node.get('style')
            if style:
                style = style.lower()
                if re.match('display *: *none', style):
                    delete.append(node)
        for node in delete:
            remove_node(node)

    def _fixIDs(self, article):
        seen_ids = set()
        for node in article.tree.xpath('//*[@id]'):
            node.set('id', safe_xml(node.get('id'), mode='id'))
            _id = node.get('id')
            while _id in seen_ids:
                _id += 'x'
                node.set('id', _id)
            seen_ids.add(_id)

    def _fixClasses(self, article):
        for node in article.tree.xpath('//*[@class]'):
            node.set('class', safe_xml(node.get('class'), mode='class'))

    def makeValidXhtml(self, article):
        self._fixIDs(article)
        self._fixClasses(article)
        self._filterTags(article)
        self._transformInvalidTags(article)
        self._removeInvalidTags(article)
        self._removeEmptyNodes(article)

    def _removeEmptyNodes(self, article):
        # Empty minimal content model according to:
        # http://www.w3.org/TR/xhtml-modularization/abstract_modules.html
        no_childs = 'br param hr input col img area frame meta link base'.split()

        todo = [article.tree]
        for root in todo:
            for leaf in root.xpath('.//*[count(child::*) = 0]'):
                if (not leaf.text or len(leaf.text)==0) and leaf.tag not in no_childs:
                    todo.append(leaf.getparent())
                    remove_node(leaf)


    def _transformInvalidTags(self, article):
        '''Transform tags invalid in an epubs to something that makes sense if possible'''

        # <u> -> <span style="text-decoration:underline;">
        # font

        queries = [{'context_node':'//center', # <center> -> <div style="text-align:center;">
                    'node':'.',
                    'repl_node':'div',
                    'repl_attrs':{'style':'text-align:center;'}
                    },
                    ]

        self.transformNodes(article, custom_queries=queries)


    def _removeInvalidTags(self, article):
        types_removed = set()
        for node in article.tree.xpath('//*[@invalid]'):
            remove_node(node)
            types_removed.add(node.tag)
        if types_removed:
            print 'INVALID IN EPUB - NODE TYPES REMOVED', types_removed

    def _filterTags(self, article):
        no_check = ['article']
        fn = os.path.join(os.path.dirname(__file__), 'tag2attr.json') # from: utils/make_tag_attr_list.py
        tag2attrs = json.load(open(fn))
        for node in article.tree.iter(tag=etree.Element):
            if node.tag in no_check:
                continue
            if node.tag not in allowed_tags:
                node.set('invalid', '1')
                continue
            allowed_attrs = tag2attrs.get(node.tag)
            for attr_name, attr_val in node.items():
                if attr_name not in allowed_attrs or \
                       (attr_val == '' and attr_name not in ['alt']):
                    del node.attrib[attr_name]


    def mapTags(self, article):
        tag_map = {'i': 'em',
                   'b': 'strong',
                   }
        tag_map_keys = tag_map.keys()
        for node in article.tree.iter():
            if node.tag in tag_map_keys:
                node.tag = tag_map[node.tag]


    def sanitize(self, article):
        for node in article.tree.iter():
            if node.text:
                node.text = node.text.replace('\r', '\n ')
            if node.tail:
                node.tail = node.tail.replace('\r', '\n ')

    def getMetaInfo(self, article):
        article.title = ''
        query = article.config('title')
        if query:
            title = article.tree.xpath(query)
            if len(title) == 1:
                article.title = title[0]
            elif len(title) == 0:
                print 'no title found'
                raise CleanerException
            else:
                print 'multiple title matches!'
                print title
                raise CleanerException

        article.attribution = ''
        query = article.config('attribution')
        if query:
            attribution = article.tree.xpath(query)
            if len(attribution) == 1:
                article.attribution = attribution[0]

    def moveNodes(self, article):
        queries = article.config('move_behind', [])
        for source, target in queries:
            source_nodes = article.tree.xpath(source)
            for source_node in source_nodes:
                target_node = source_node.xpath(target)
                if target_node:
                    target_node[0].addnext(source_node)

    def transformNodes(self, article, custom_queries=[]):
        queries = custom_queries or article.config('transform')
        if not queries:
            return
        #for root_query, node_query, new_node_type in queries:
        for query in queries:
            for root in article.tree.xpath(query['context_node']):
                node = root.xpath(query['node'])
                if len(node) == 1:
                    node = node[0]
                    p = root.getparent()
                    if len(p):
                        children = node.getchildren()
                        new = etree.Element(query['repl_node'], **query['repl_attrs'])
                        new.extend(children)
                        new.text = node.text
                        new.tail = node.tail
                        p.replace(root, new)

    def removeNodes(self, article):
        queries = article.config('remove', [])
        for klass in article.config('remove_class', []):
            queries.append('.//*[@class="{0}" or contains(@class, " {0} ") or re:match(@class, "^{0} " ) or re:match(@class, " {0}$" )]'.format(klass))
        for id in article.config('remove_id', []):
            queries.append('//*[@id="{0}" or contains(@id, " {0} ") or re:match(@id, "^{0} " ) or re:match(@id, " {0}$" )]'.format(klass))
        for query in queries:
            for node in article.tree.xpath(query,namespaces={'re':'http://exslt.org/regular-expressions'}):
                remove_node(node)

    def applyXSLT(self, article):
        xslt_frag = article.config('xslt')
        if not xslt_frag:
            return
        xslt_query = '\n'.join([self.xslt_head, xslt_frag, self.xslt_foot])
        xslt_doc = etree.parse(StringIO(xslt_query))
        transform = etree.XSLT(xslt_doc)
        article.tree = transform(article.tree).getroot()
