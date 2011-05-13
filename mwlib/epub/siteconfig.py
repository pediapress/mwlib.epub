#! /usr/bin/env python
#! -*- coding:utf-8 -*-

import urlparse

# content: 'xpath-expr' query which selects the content that is supposed to be printed
# remove: 'xpath-expr' query that selects elements which are supposed to be removed
# remove_class: [classnames] shorthand to remove elements containing a class
# remove_id: same as above for id's

fallback = {'figure':{'container': '//*[@width>100]',
                      'images': './/img[@width>(0.9*$cwidth) and @width<(1.1*$cwidth)]',
                      'caption': './/*[not(descendant-or-self::img)]',
                      },
            'content': '//div[@id="content"]',
            }

_default_config = [
    ('http://wikipedia.org',
     {'remove_class':['editsection',
                      'toc',
                      'noprint',
                      ],
      'remove':[],
      }),
    ]

default_config = dict(_default_config)



class SiteConfigHandler(object):

    def __init__(self, custom_siteconfig=None):
        self.verbose = False
        self.siteconfig = default_config
        if custom_siteconfig:
            self.siteconfig.update(custom_siteconfig)

    def _getMatchingSite(self, url):
        getFrags = lambda u: urlparse.urlsplit(u).netloc.split('.')[::-1]
        matches =[]
        url_frags = getFrags(url)
        for site in self.siteconfig.keys():
            site_frags = getFrags(site)
            score = 0
            for i in range(min(len(url_frags), len(site_frags))):
                if url_frags[i] == site_frags[i]:
                    score += 1
                else:
                    break
            matches.append((score, site))
        matches.sort(reverse=True)
        if matches[0][0]>1: # domain matched at least
            return matches[0][1]
        return None
                
    def get(self, url, key, default=None):
        if url.startswith('file'):
            site = 'local'
        else:
            site = self._getMatchingSite(url)
        if not site and self.verbose:
            print 'WARNING: no matching site in config for url: ', url
        res = self.siteconfig.get(site, {}).get(key) or fallback.get(key)
        if res == None:
            return default
        else:
            return res
