
import os
import json

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import memcache

import config
import pypi_cron

def build_data():
    packages_list = pypi_cron.get_packages_list_from_cache_or_pypi()
    good = 0
    total = len(packages_list)
    min_time = None
    for pkg in packages_list:
        if pkg.py3 or pkg.equivalent_url or pkg.force_green:
            good += 1
        if min_time is None:
            min_time = pkg.timestamp
        elif pkg.timestamp is not None and pkg.timestamp < min_time:
            min_time = pkg.timestamp
    
    if total > 0:
        status = 1.0 * good / total
    else:
        status = 0
    
    if status < 0.5:
        title = 'Python 3 Wall of Shame'
    else:
        title = 'Python 3 Wall of Superpowers'
    
    template_values = {
        'title': title,
        'packages': packages_list,
        'count': "%d/%d" % (good, total),
        'min_time': min_time,
        }
    return template_values

def get_html():
    path = os.path.join(os.path.dirname(__file__), 'index_db.html')
    # 2018-04-22 killing the building of data
    #template_values = build_data()
    template_values = json.load(open("rip/template-data.json"))
    html = template.render(path, template_values)
    return html

class DatabaseMainPage(webapp.RequestHandler):
    def get(self):
        showdata = self.request.get('showdata', None)
        if showdata is not None:
            self.response.out.write(json.dumps(build_data()))
            return
        nocache = self.request.get('nocache', None)
        if nocache is not None:
            self.response.out.write(get_html())
            return

        html = memcache.get(config.HTML_CACHE_KEY)
        if html is None:
            # 5 hour cache
            html = get_html()
            memcache.add(config.HTML_CACHE_KEY, html, 60 * 60 * 5)
        self.response.out.write(html)


