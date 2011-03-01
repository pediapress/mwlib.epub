#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import os
import shutil
import zipfile
import tempfile

from collections import namedtuple

from lxml import etree
from lxml.builder import ElementMaker

from mwlib.epub import config
from mwlib.epub.treeprocessor import TreeProcessor
from mwlib.epub.collection import coll_from_zip


ArticleInfo = namedtuple('ArticleInfo', 'id path title')

def serialize(f):
    return lambda : etree.tostring(f(), pretty_print=True)    

class EpubContainer(object):

    def __init__(self, fn):
        self.zf = zipfile.ZipFile(fn, 'w', compression=zipfile.ZIP_DEFLATED)
        self.zf.debug = 3
        self.added_files = set()
        self.write_mime_type()
        self.write_meta_inf()

        self.articles =[]

        self.coll = {'title': 'FIXME - testtitle',
                     'author': 'FIXME - testauthor',
                     } # FIXME
        
    def add_file(self, fn, content, compression=True):
        if fn in self.added_files:
            return
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        self.zf.writestr(fn, content)
        self.added_files.add(fn)

    def link_file(self, fn, arcname, compression=True):
        if fn in self.added_files:
            return
        compression_flag = zipfile.ZIP_DEFLATED if compression else zipfile.ZIP_STORED
        self.zf.write(fn, arcname, compression_flag)
        self.added_files.add(fn)

    def write_mime_type(self):
        fn = os.path.join(os.path.dirname(__file__), 'mimetype')
        self.link_file(fn, 'mimetype', compression=False)

    def write_meta_inf(self):
        opf_content=u'''<?xml version="1.0" encoding="UTF-8" ?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="%(opf_fn)s" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
''' % {'opf_fn': config.opf_fn}
        self.add_file(fn=config.meta_inf_fn, content=opf_content)

    def close(self):
        self.writeOPF()
        self.writeNCX()
        self.zf.close()

    def writeNCX(self):
        E = ElementMaker()

        tree = E.ncx({'version': '2005-1',
                      'xmlns': 'http://www.daisy.org/z3986/2005/ncx/'},
                     E.head(*[E.meta({'name': item[0],
                                      'content': item[1]}
                                      ) for item in [("dtb:uid", "123456789X"),
                                                     ("dtb:depth", "1"),
                                                     ("dtb:totalPageCount", '0'),
                                                     ("dtb:maxPageNumber", '0') ]]),
                     E.docTitle(E.text(self.coll.get('title', 'Untitled'))),
                     E.docAuthor(E.text(self.coll.get('author', 'NN'))),
                     )

        nav_map = E.navMap(*[E.navPoint({'id': article.id,
                                         'playorder': str(idx)},
                                        E.navLabel(E.text(article.title)),
                                        E.content(src=article.path)
                                        ) for (idx, article) in enumerate(self.articles)])
        tree.append(nav_map)
        xml = etree.tostring(tree, method='xml', encoding='utf-8',pretty_print=True, xml_declaration=True)
        self.add_file(config.ncx_fn, xml)

    def writeOPF(self):
        nsmap = {'dc': "http://purl.org/dc/elements/1.1/",
                 'opf': "http://www.idpf.org/2007/opf/"}
        E = ElementMaker()

        def writeOPF_metadata():
            E = ElementMaker(nsmap=nsmap)
            DC = ElementMaker(namespace=nsmap['dc'])
            author = self.coll.get('author', 'NN')
            tree = E.metadata(DC.title('FIXME - title'),
                              DC.creator('FIXME - %s' % author,
                                         {'{%s}role' % nsmap['opf']: 'aut',
                                          '{%s}file-as' % nsmap['opf']: author}))
            return tree

        def writeOPF_manifest():
            tree = E.manifest()
            tree.extend([E.item({'id': article.id,
                                 'href': article.path,
                                 'media-type': 'application/xhtml+xml'})
                         for article in self.articles])
            tree.append(E.item({'id':'ncx',
                                'href': os.path.basename(config.ncx_fn),
                                'media-type': 'application/x-dtbncx+xml'}))
            #FIXME add missing resources:
            # images
            # css
            return tree
        
        def writeOPF_spine():
            tree = E.spine({'toc': 'ncx'},
                           *[E.itemref(idref=article.id)
                             for article in self.articles])
            return tree

        tree = E.package({'version': "2.0",
                          'xmlns': nsmap['opf'],
                         'unique-identifier': '42'}) # FIXME: use real bookid
        tree.extend([writeOPF_metadata(),
                     writeOPF_manifest(),
                     writeOPF_spine()]
                     )
        #FIXME: check if guide section should be written
        xml = etree.tostring(tree, method='xml', encoding='utf-8',pretty_print=True, xml_declaration=True)
        self.add_file(config.opf_fn, xml)

    def addArticle(self, webpage):
        path = 'OPS/%s.xhtml' % webpage.id
        self.add_file(path, webpage.xml)
        self.articles.append(ArticleInfo(id=webpage.id,
                                         path=os.path.basename(path),
                                         title=webpage.title))

        for img_src, img_fn in webpage.images.items():
            zip_fn = os.path.join(config.img_abs_path, os.path.basename(img_fn))
            self.link_file(img_fn, zip_fn, compression=False)

class EpubWriter(object):

    def __init__(self, output, coll):
        self.output = output
        self.target_dir = os.path.dirname(output)
        self.coll = coll

    def initContainer(self):
        if not os.path.exists(self.target_dir):
            print 'created dir'
            os.makedirs(self.target_dir)
        self.container = EpubContainer(self.output)

    def closeContainer(self):
        self.container.close()

    def renderColl(self):
        self.initContainer()

        for lvl, webpage in self.coll.outline.walk():
            self.processWebpage(webpage)

        self.closeContainer()

    def processWebpage(self, webpage):
        tree = webpage.tree

        self.tree_processor = TreeProcessor()

        #self.tree_processor.getMetaInfo(webpage)
        self.tree_processor.clean(webpage)

        self.remapLinks(webpage)
        webpage.xml = self.serializeArticle(tree)
        self.container.addArticle(webpage)

    def remapLinks(self, webpage):
        for img in webpage.tree.findall('.//img'):
            img_fn = webpage.images.get(img.attrib['src'])
            if img_fn:
                zip_rel_path = os.path.join(config.img_rel_path, os.path.basename(img_fn))
                img.attrib['src'] = zip_rel_path

        #FIXME: fix paths of css and other resource files.
        #intra-collection links need to be detected and remapped as well

    def serializeArticle(self, node):
        assert not node.find('.//body'), 'error: node contains BODY tag'
        E = ElementMaker()
        html = E.html({'xmlns':"http://www.w3.org/1999/xhtml"},
                      E.head(E.meta({'http-equiv':"Content-Type",
                                     'content': "application/xhtml+xml; charset=utf-8"})
                             ),
                      E.body(node
                             ),
                      )

        xml = etree.tostring(html,
                             encoding='utf-8',
                             method='xml',
                             xml_declaration=False,
                             pretty_print=True,
                             )
        xml = '\n'.join(['<?xml version="1.0" encoding="UTF-8" ?>',
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">',
                         xml])

        return xml



def writer(env, output,
           status_callback=None,
           ):
    if status_callback:
        status_callback(status='generating epubfile')

    tmpdir = tempfile.mkdtemp()
    zipfn = env
    coll = coll_from_zip(tmpdir, zipfn)

    epub = EpubWriter(output, coll)
    epub.renderColl()
    shutil.rmtree(tmpdir)
    print 'generated epub file'

writer.description = 'epub Files'
writer.content_type = 'application/epub+zip'
writer.file_extension = 'epub'

