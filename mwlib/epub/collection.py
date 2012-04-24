#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.


# from gevent import monkey
# monkey.patch_all()

from hashlib import sha1
from lxml import etree
import os
import re
import urllib2
import urlparse
import shutil
import subprocess

#from gevent.pool import Pool
try:
    import simplejson as json
except ImportError:
    import json

from mwlib.epub.siteconfig import SiteConfigHandler

known_image_exts = set(['.jpg', '.jpeg', '.gif', '.png']) # FIXME


def safe_path(url):
    parts = urlparse.urlparse(url)
    s = '-'.join([parts.netloc, parts.path, sha1(url).hexdigest()[:6]])
    return re.sub('[^-_.a-zA-Z0-9]', '_', s)


class Chapter(object):
    def __init__(self, title):
        self.title = title
        self.items = []

    def as_dict(self):
        return {
            'type': 'chapter',
            'title': self.title,
            'items': [item.as_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, coll, data):
        c = cls(data['title'])
        for item in data.get('items', []):
            if item['type'] == 'webpage':
                c.items.append(WebPage.from_dict(coll, item))
            elif item['type'] == 'chapter':
                c.items.append(Chapter.from_dict(item))
        return c


class WebPage(object):
    "Resource GETtable via HTTP, described by URL"

    def __init__(self, coll, title, url, images=None, user_agent=None):
        self.coll = coll
        self.title = title
        self.url = url
        self.id = safe_path(self.url)
        self.basedir = self.coll.get_path(self.id)
        if not os.path.isdir(self.basedir):
            os.makedirs(self.basedir)
        self.images = images or {}
        self.user_agent = user_agent

    def as_dict(self):
        return {
            'type': 'webpage',
            'title': self.title,
            'url': self.url,
            'images': self.images,
            'user_agent': self.user_agent,
        }

    @classmethod
    def from_dict(cls, coll, data):
        res = cls(coll,
                  title=data['title'],
                  url=data['url'],
                  images=data['images'],
                  user_agent=data['user_agent'],
                  )
        res.tree = res._get_parse_tree()
        return res

    def get_path(self, p):
        return os.path.join(self.basedir, p)

    def fetch_url(self, url):
        print 'fetching %s' % url
        req = urllib2.Request(url)
        if self.user_agent:
            req.add_header('User-agent', self.user_agent)
        data = urllib2.urlopen(req).read()
        return data

    def _add_hires_img_src(self, node):
        regexpNS = "http://exslt.org/regular-expressions"
        path_query = self.config('hires_path')
        hires_img_query = self.config('hires_images')
        if not hires_img_query:
            return
        for img in node.xpath(hires_img_query):
            if img.attrib.get('src'):
                hires_path = img.xpath(path_query, namespaces={'re':regexpNS}).strip()
                img.set('hiressrc', hires_path)

    def handleCss(self, article):
        css_fn = 'wp.css' # FIXME make this configurable

        css_path_orig = os.path.join(os.path.dirname(__file__), css_fn)
        css_path = self.get_path(css_fn)
        try:
            shutil.copy(css_path_orig, css_path)
        except IOError:
            print 'css file not found'
            return
        self.css_path = css_path

        link = etree.Element('link',
                            rel='stylesheet',
                            href=self.css_path,
                            type='text/css')

        head = article.xpath('//head')
        if not head:
            head = etree.Element('head')
            article.insert(0, head)
        head.append(link)
        article.set('css_fn', css_path)

    def _tidy(self, html):
        import tidy
        tidy_opts = { # http://tidy.sourceforge.net/docs/quickref.html
            "output-xhtml": True,
            "tidy-mark": False,
            "alt-text": "",
            "doctype": 'strict',
            "force-output": True,
            # 'clean':True,
            'char-encoding': 'utf8',
            }
        return tidy.parseString(html, **tidy_opts).__str__()

    def _get_parse_tree(self, data=None):
        if not data:
            data = open(self.get_path('content.orig')).read()
        # data = self._tidy(data)
        data = unicode(data, 'utf-8', 'ignore') # FIXME: get the correct encoding!
        root = etree.HTML(data) # FIXME: base_url?
        content_filter = self.config('content')
        if content_filter:
            content = root.xpath(content_filter)
        else:
            content = root
        art = etree.Element('article')
        art.extend(content)

        self.handleCss(art)

        self._add_hires_img_src(art)
        return art

    def fetch(self):
        content = self.fetch_url(self.url)
        open(self.get_path('content.orig'), 'wb').write(content)
        self.tree = self._get_parse_tree(data=content)
        self.fetch_images()

    def fetch_images(self, num_conns=10, urls=None):
        if urls:
            srcs = urls
        else:
            srcs = set()
            for img in self.tree.xpath('//img'):
                # FIXME: thumbnail and hires images are fetched, only fetch hires if available.
                # if fetch error for hires occurs fallback to low res
                for src in [img.attrib.get('hiressrc'), img.attrib.get('src')]:
                    if src:
                        srcs.add(src.strip())

        def fetch(src):
            url = urlparse.urljoin(self.url, src)
            filename = self.coll.get_image_filename(url)
            if not filename:
                return
            self.images[src] = filename
            if os.path.exists(filename):
                return
            data = self.fetch_url(url)
            if not data:
                return
            open(filename, 'w').write(data)

        while srcs:
            fetch(srcs.pop())

        # pool = Pool(num_conns)
        # pool.map(fetch, srcs)

    def config(self, key, default=None):
        return self.coll.siteconfig.get(self.url, key, default=default)


class Outline(object):
    def __init__(self, coll):
        self.coll = coll
        self.items = []

    def append(self, item):
        self.items.append(item)

    def as_dict(self):
        return {
            'type': 'outline',
            'items': [item.as_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, coll, data):
        o = cls(coll)
        for item in data.get('items', []):
            if item['type'] == 'webpage':
                o.items.append(WebPage.from_dict(coll, item))
            elif item['type'] == 'chapter':
                o.items.append(Chapter.from_dict(coll, item))
        return o

    def walk(self, cls=None):
        def get_items(items, level=0):
            for item in items:
                yield level, item
                get_items(getattr(item, 'items', []), level=level+1)

        for level, item in get_items(self.items):
            if cls is None or isinstance(item, cls):
                yield level, item


class Collection(object):
    def __init__(self, basedir, title=None, subtitle=None, editor=None, custom_siteconfig=None):
        self.basedir = basedir
        self.title = title
        self.subtitle = subtitle
        self.editor = editor
        self.outline = Outline(self)
        self.custom_siteconfig = custom_siteconfig
        self.siteconfig = SiteConfigHandler(custom_siteconfig=custom_siteconfig)
        self.url2webpage = {}

    def dump(self):
        data = {
            'title': self.title,
            'subtitle': self.subtitle,
            'editor': self.editor,
            'outline': self.outline.as_dict(),
            'custom_siteconfig': self.custom_siteconfig,
        }
        json.dump(data, open(self.get_path('meta.json'), 'wb'), indent=4)

    def load(self):
        data = json.load(open(self.get_path('meta.json')))
        self.title = data['title']
        self.subtitle = data['subtitle']
        self.editor = data['editor']
        self.outline = Outline.from_dict(self, data['outline'])
        self.custom_siteconfig=data['custom_siteconfig']
        self.siteconfig = SiteConfigHandler(custom_siteconfig=self.custom_siteconfig)

    def get_path(self, fn):
        return os.path.join(self.basedir, fn)

    def get_image_filename(self, url):
        ext = os.path.splitext(url)[1].lower()
        if ext not in known_image_exts:
            print 'unknown image extension in url %r' % url
            return None
        d = self.get_path('images')
        if not os.path.isdir(d):
            os.makedirs(d)
        return os.path.join(d, safe_path(url)[:60] + ext)

    def fetch(self):
        for level, webpage in self.outline.walk(cls=WebPage):
            webpage.fetch()

    def append(self, wp):
        self.outline.append(wp)
        if isinstance(wp, WebPage):
            self.url2webpage[wp.canonical_url] = wp

scaled_images = {}
def limit_size(img, fn):
    width = int(img.get('width') or '0')
    src = img.attrib['src']
    if src in scaled_images:
        return scaled_images[src]
    if width:
        target_fn = '%s_small%s' % (fn, os.path.splitext(fn)[1])
        cmd = ['convert',
               fn,
               '-resize', '%d' % width,
               target_fn,
               ]
        try:
            err = subprocess.call(cmd)
        except OSError:
            err = True

        if not err:
            scaled_images[src] = target_fn
            return target_fn
        else:
            print 'ERROR: scaling down image failed', src, fn
    return fn

def coll_from_zip(basedir, env, status_callback=None):

    def img_ext_correct(fn):
        from PIL import Image
        img = Image.open(fn)
        fmt = '.' + img.format.lower()
        name, ext = os.path.splitext(fn)
        ext = ext.lower()
        if ext == '.jpg':
            ext = '.jpeg'
        if fmt != ext:
            return (False, name + fmt)
        else:
            return (True, fn)

    if isinstance(env, basestring):
        from mwlib import wiki
        env = wiki.makewiki(env)

    coll = Collection(basedir=basedir,
                      title=env.metabook.title or '',
                      subtitle=env.metabook.subtitle or '',
                      editor=env.metabook.editor or '',
                      )
    missing_images = []
    progress_inc = 100.0/len(env.metabook.items)
    for n, item in enumerate(env.metabook.walk()):
        if item.type == 'chapter':
            chapter = Chapter(item.title)
            coll.append(chapter)
            continue
        elif item.type == 'custom':
            # a "custom" item currently can be the preface added at pediapress.com
            # FIXME: support custom item
            continue
        title = item.title
        url = item.wiki.getURL(title, item.revision)

        data = item.wiki.getHTML(title, item.revision)

        html = data['text']['*']
        assert isinstance(title, unicode) and isinstance(html, unicode) and isinstance(url, unicode)
        html = '<div id="content"><h1>%s</h1>\n\n%s</div>' % (title.encode('utf-8'), html.encode('utf-8'))

        wp = WebPage(coll, title, url, user_agent='Mozilla/5.0') # images
        wp.canonical_url = urlparse.urljoin(item._env.wiki.siteinfo['general']['base'], urllib2.quote(title.replace(' ', '_').encode('utf-8')).decode('utf-8'))

        open(wp.get_path('content.orig'), 'wb').write(html)
        wp.tree = wp._get_parse_tree(html)

        for img in wp.tree.xpath('.//img'):
            src  = img.attrib['src']
            frags = src.split('/')
            if len(frags):
                fn = None
                for title in [frags[-2], frags[-1]]:
                    title = urlparse.unquote(title.encode('utf-8')).decode('utf-8')
                    fn = item.wiki.env.images.getDiskPath(title)
                    if fn:
                        correct, new_fn = img_ext_correct(fn)
                        if not correct:
                            os.rename(fn, new_fn)
                            fn = new_fn
                        fn = limit_size(img, fn)
                        wp.images[src] = fn
                        break
                if not fn and title not in missing_images:
                    print 'image not found %r' % src
                    missing_images.append(title)

        coll.append(wp)
        if status_callback:
            status_callback(progress=n*progress_inc)
    return coll

if __name__ == '__main__':

    import sys
    zip_fn = sys.argv[1]
    col_base_dir = sys.argv[2]
    coll = coll_from_zip(col_base_dir, zip_fn)
    coll.dump()
    print 'converted zip to coll'
