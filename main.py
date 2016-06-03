
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import memcache

import config

def build_data():
    packages = db.GqlQuery("SELECT * FROM Package ORDER BY downloads DESC LIMIT 200")
    
    good = 0
    packages_list = list(packages)
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
    template_values = build_data()
    html = template.render(path, template_values)
    return html

class DatabaseMainPage(webapp.RequestHandler):
    def get(self):
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


