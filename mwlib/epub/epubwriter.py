#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import os
import shutil
import zipfile
import tempfile
import mimetypes
import urlparse
from xml.sax.saxutils import escape as xmlescape

from pprint import pprint

from collections import namedtuple

from lxml import etree
from lxml.builder import ElementMaker

from mwlib.epub import config
from mwlib.epub.treeprocessor import TreeProcessor, safe_xml_id, clean_url, remove_node
from mwlib.epub import collection


ArticleInfo = namedtuple('ArticleInfo', 'id path title type')

def serialize(f):
    return lambda : etree.tostring(f(), pretty_print=True)


class EpubContainer(object):

    def __init__(self, fn, coll):
        self.zf = zipfile.ZipFile(fn, 'w', compression=zipfile.ZIP_DEFLATED)
        self.zf.debug = 3
        self.added_files = set()
        self.write_mime_type()
        self.write_meta_inf()

        self.articles =[]

        self.coll = coll

    def add_file(self, fn, content, compression=True):
        if fn in self.added_files:
            return
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        self.zf.writestr(fn, content)
        self.added_files.add(fn)

    def link_file(self, fn, arcname, compression=True):
        if arcname in self.added_files:
            return
        compression_flag = zipfile.ZIP_DEFLATED if compression else zipfile.ZIP_STORED
        self.zf.write(fn, arcname, compression_flag)
        self.added_files.add(arcname)

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
                     E.docTitle(E.text(self.coll.title)),
                     E.docAuthor(E.text(self.coll.editor)),
                     )


        nav_map = E.navMap()
        last_chapter = None
        for (idx, article) in enumerate(self.articles):
            nav_point = E.navPoint({'id': article.id,
                                    'playOrder': str(idx+1)},
                                   E.navLabel(E.text(article.title)),
                                   E.content(src=article.path))
            if article.type == 'article' and last_chapter != None:
                last_chapter.append(nav_point)
                continue
            if article.type == 'chapter':
                last_chapter = nav_point
            nav_map.append(nav_point)

        tree.append(nav_map)
        xml = etree.tostring(tree, method='xml', encoding='utf-8',pretty_print=True, xml_declaration=True)

        self.add_file(config.ncx_fn, xml)

    def writeOPF(self):
        nsmap = {'dc': "http://purl.org/dc/elements/1.1/",
                 'opf': "http://www.idpf.org/2007/opf"}
        E = ElementMaker()

        def writeOPF_metadata():
            E = ElementMaker(nsmap=nsmap)
            DC = ElementMaker(namespace=nsmap['dc'])
            # author = self.coll.editor
            tree = E.metadata(DC.identifier({'id':'bookid'}, 'bla'),
                              DC.language('en'), # FIXME
                              DC.title(self.coll.title or 'untitled'),
                              # DC.creator(author,  # FIXME
                              #            {'{%s}role' % nsmap['opf']: 'aut',
                              #             '{%s}file-as' % nsmap['opf']: author})
                              )
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
            for fn in self.added_files:
                if fn.startswith('OPS/'):
                    fn = fn[4:]
                mimetype, encoding = mimetypes.guess_type(fn)
                if mimetype in ['text/css',
                                'image/png',
                                'image/jpeg',
                                'image/gif',
                                ]:
                    tree.append(E.item({'id': safe_xml_id(fn),
                                        'href': fn,
                                        'media-type': mimetype}))


            return tree

        def writeOPF_spine():
            tree = E.spine({'toc': 'ncx'},
                           *[E.itemref(idref=article.id)
                             for article in self.articles])
            return tree

        tree = E.package({'version': "2.0",
                          'xmlns': nsmap['opf'],
                          'unique-identifier': 'bookid'}) # FIXME: use real bookid


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
        self.articles.append(ArticleInfo(id=safe_xml_id(webpage.id),
                                         path=os.path.basename(path),
                                         title=webpage.title,
                                         type='article' if isinstance(webpage, collection.WebPage) else 'chapter'))


        if getattr(webpage, 'tree', False) != False:
            css_fn = webpage.tree.get('css_fn')
            self.link_file(css_fn, 'OPS/wp.css') # fixme proper name
            used_images = [src[len(config.img_rel_path):] for src in webpage.tree.xpath('//img/@src')]
        else:
            used_images = []

        if getattr(webpage, 'images', False) != False:
            for img_src, img_fn in webpage.images.items():
                basename = os.path.basename(img_fn)
                if basename not in used_images:
                    continue
                zip_fn = os.path.join(config.img_abs_path, basename)
                self.link_file(img_fn, zip_fn, compression=False)


class EpubWriter(object):

    def __init__(self, output, coll):
        self.output = output
        self.target_dir = os.path.dirname(output)
        self.coll = coll
        self.scaled_images = {}

    def initContainer(self):
        if not os.path.exists(self.target_dir):
            print 'created dir'
            os.makedirs(self.target_dir)
        self.container = EpubContainer(self.output, self.coll)

    def closeContainer(self):
        self.container.close()

    def renderColl(self):
        self.initContainer()
        self.processTitlePage()
        for lvl, webpage in self.coll.outline.walk():
            if isinstance(webpage, collection.WebPage):
                self.processWebpage(webpage)
            elif isinstance(webpage, collection.Chapter):
                self.processChapter(webpage)

        self.closeContainer()

    def processTitlePage(self):
        if not any(txt != '' for txt in [self.coll.title,
                                         self.coll.subtitle,
                                         self.coll.editor]):
            return
        titlepage = collection.Chapter(self.coll.title)
        titlepage.id = 'titlepage'
        titlepage.images = {}
        # titlepage.images['title.png'] = os.path.join(os.path.dirname(__file__), 'title.png')
        titlepage.xml = '''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>%(title)s</title></head>
<body>

<!-- <div><img src="images/title.png" width="600" alt="" /></div> -->


<h1 style="margin-top:20%%;font-size:300%%;text-align:center;">%(title)s</h1>
<h2 style="margin-top:1em;font-size:200%%;text-align:center;">%(subtitle)s</h2>
<h3 style="margin-top:1em;font-size:100%%;text-align:center;">%(editor)s</h3>

</body>
</html>
        ''' % dict(title=xmlescape(self.coll.title),
                   subtitle=xmlescape(self.coll.subtitle),
                   editor=xmlescape(self.coll.editor),)
        self.container.addArticle(titlepage)

    def processChapter(self, chapter):
        self.num_chapters = getattr(self, 'num_chapters', 0) + 1
        chapter.id = 'chapter_%02d' % self.num_chapters
        chapter.xml = '''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>%(title)s</title></head>
<body><h1 style="margin-top:15%%;font-size:300%%;text-align:center;">%(title)s</h1></body>
</html>
        ''' % dict(title=xmlescape(chapter.title))

        self.container.addArticle(chapter)


    def processWebpage(self, webpage):
        from copy import copy
        self.remapLinks(webpage)
        self.tree_processor = TreeProcessor()
        #self.tree_processor.getMetaInfo(webpage)
        self.tree_processor.annotateNodes(webpage)
        self.tree_processor.clean(webpage)
        webpage.xml = self.serializeArticle(copy(webpage.tree))
        self.container.addArticle(webpage)


    def remapLinks(self, webpage):
        for img in webpage.tree.findall('.//img'):
            img_fn = webpage.images.get(img.attrib['src'])
            if img_fn:
                zip_rel_path = os.path.join(config.img_rel_path, os.path.basename(img_fn))
                img.attrib['src'] = zip_rel_path
            else:
                remove_node(img)
        #FIXME: fix paths of css and other resource files.
        #intra-collection links need to be detected and remapped as well
        for link in webpage.tree.findall('.//link'):
            link.set('href','wp.css')

        target_ids =  webpage.tree.xpath('.//@id')
        for a in webpage.tree.findall('.//a'):
            href = a.get('href')
            if not href: # this link is probably just an anchor
                continue
            if href.startswith('#'):
                target_id = safe_xml_id(href)[1:]
                if target_id not in target_ids:
                    a.set('id', target_id)
                    target_ids.append(target_id)
                a.set('href', '#'+target_id)
            else:
                url = clean_url(urlparse.urljoin(webpage.url, href))
                linked_wp = webpage.coll.url2webpage.get(url)
                if linked_wp:
                    a.set('href', linked_wp.id + '.xhtml')
                else:
                    a.set('href', url)

    def serializeArticle(self, node):
        assert not node.find('.//body'), 'error: node contains BODY tag'
        E = ElementMaker()

        html = E.html({'xmlns':"http://www.w3.org/1999/xhtml"},
                      E.head(E.meta({'http-equiv':"Content-Type",
                                     'content': "application/xhtml+xml; charset=utf-8"})
                             ),
                      )

        head = html.find('.//head')
        node_head = node.find('.//head')
        for head_content in node_head.iterchildren():
            head.append(head_content)
        node_head.getparent().remove(node_head)

        body = E.body()
        html.append(body)
        body.extend(node)

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
           validate=True,
           ):
    if status_callback:
        status_callback(status='generating epubfile')

    tmpdir = tempfile.mkdtemp()
    zipfn = env
    coll = collection.coll_from_zip(tmpdir, zipfn)

    epub = EpubWriter(output, coll)
    epub.renderColl()
    shutil.rmtree(tmpdir)

    if validate:
        import subprocess
        cmd = ['epubcheck', output]
        cmd = 'epubcheck {0}'.format(output)
        p = subprocess.Popen(cmd,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        try:
            stdout, stderr = p.communicate()
            ret = p.returncode
        except OSError, e:
            print 'WARNING: epubcheck not found - epub not validated'
            print 'ERROR', e
        else:
            print 'VALIDATING EPUB'
            print 'validation result:', ret
            print stdout
            print stderr

writer.description = 'epub Files'
writer.content_type = 'application/epub+zip'
writer.file_extension = 'epub'

