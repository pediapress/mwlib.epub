#! /usr/bin/env python
#! -*- coding:utf-8 -*-

from StringIO import StringIO
from lxml import etree


class CleanerException(Exception):
    pass

class TreeProcessor(object):

    tag_blacklist = 'script embed object param style'.split()

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


    def clean(self, article):
        self.sanitize(article)
        self.mapTags(article)
        self.removeNodesCustom(article)
        self.moveNodes(article)
        self.applyXSLT(article)
        self.removeTags(article.tree)


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

    def removeNodesCustom(self, article):
        queries = article.config('remove', [])
        for klass in article.config('remove_class', []):
            queries.append('.//*[contains(@class, "{0}")]'.format(klass))
        for id in article.config('remove_id', []):
            queries.append('.//*[contains(@id, "{0}")]'.format(id))
        for query in queries:
            for node in article.tree.xpath(query):
                p = node.getparent()
                if len(p):
                    p.remove(node)

    def applyXSLT(self, article):
        xslt_frag = article.config('xslt')
        if not xslt_frag:
            return
        xslt_query = '\n'.join([self.xslt_head, xslt_frag, self.xslt_foot])
        xslt_doc = etree.parse(StringIO(xslt_query))
        transform = etree.XSLT(xslt_doc)
        article.tree = transform(article.tree).getroot()


    def removeTags(self, root):
        for node_type in self.tag_blacklist:
            for node in root.iter(tag=node_type):
                node.getparent().remove(node)
                # FIXME: handle tail text
    
        #     # if c.tail:
        #     #         prev = c.getprevious()
        #     #         prev_tail = prev.tail or ''
        #     #         prev.tail = prev_tail + c.tail
        #     node.remove(c)
