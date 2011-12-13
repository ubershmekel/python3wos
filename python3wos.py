
from google.appengine.dist import use_library
use_library('django', '0.96')

import os
from google.appengine.ext.webapp import template
import cgi
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.api import memcache

from PypiPackage import Package

HTML_CACHE_KEY = "WOShtml"


def build_data():
    packages = db.GqlQuery("SELECT * FROM Package ORDER BY downloads DESC LIMIT 200")
    
    good = 0
    packages_list = list(packages)
    total = len(packages_list)
    min_time = None
    for pkg in packages_list:
        if pkg.py3:
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


class DatabaseMainPage(webapp.RequestHandler):
    def get(self):
        html = memcache.get(HTML_CACHE_KEY)
        if html is None:
            path = os.path.join(os.path.dirname(__file__), 'index_db.html')
            template_values = build_data()
            html = template.render(path, template_values)
            # 5 hour cache
            memcache.add(HTML_CACHE_KEY, html, 60 * 60 * 5)
        
        self.response.out.write(html)

application = webapp.WSGIApplication(
                                     [
                                       ('/', DatabaseMainPage),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
