#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Jin'
SITENAME = u'Living@Greatwall'
SITEURL = u'http://yangjin-unique.github.io'

PATH = 'content'

TIMEZONE = 'Asia/Shanghai'

DEFAULT_LANG = u'en'

THEME = "pelican-bootstrap3"


STATIC_PATHS = ['images', 'pdfs']

# plugins
PLUGIN_PATHS = [u'../pelican-plugins']
PLUGINS = [u'sitemap', u'disqus_static']

# disqus
DISQUSURL = u'http://yangjin-unique.github.io'
DISQUS_SITENAME = u'yangjin-unique'
DISQUS_SECRET_KEY = u'dRUdIUTxTWjZcbVZoChJZzyqVzFYUyykVCrlxNIIh1iYqo4FRX5nFT9NXhaWZAtV'
DISQUS_PUBLIC_KEY = u'REklPrrLsBAzZmE7SmVIJEXfRWUjtPd2MhHoMBjIgvOcFW2QBuZFYPoBz835k9mY'

SITEMAP = {
    "format": "xml",
    "priorities": {
        "articles": 0.7,
        "indexes": 0.5,
        "pages": 0.3,
    },
    "changefreqs": {
        "articles": "monthly",
        "indexes": "daily",
        "pages": "monthly",
    }
}

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
        ('Online Linux Kernel Source Code', 'http://lxr.free-electrons.com'),
        ('酷壳CoolShell', 'http://coolshell.cn'),
        )


# Social widget
#SOCIAL = (

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True
