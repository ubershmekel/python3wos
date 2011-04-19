import os
from google.appengine.ext.webapp import template
import cgi
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail

from PypiPackage import Package

class MainPage(webapp.RequestHandler):
    def get(self):
        count = open('count.txt').read()
        # note that count.txt contains something akin to '13/100' so the '.0'
        # is a hack to force float division. Pardon my hackery.
        if eval(count + '.0') < 0.5:
            title = 'Python 3 Wall of Shame'
        else:
            title = 'Python 3 Wall of Superpowers'
        
        template_values = {
            'title': title,
            'results_table': open('results.html').read(),
            'date': open('date.txt').read(),
            'count': count,
            }
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

def build_data():
    packages = db.GqlQuery("SELECT * FROM Package ORDER BY downloads DESC LIMIT 200")
    
    good = 0
    packages_list = list(packages)
    total = len(packages_list)
    for pkg in packages_list:
        if pkg.py3:
            good += 1
    # note that count.txt contains something akin to '13/100' so the '.0'
    # is a hack to force float division. Pardon my hackery.
    status = 1.0 * good / total
    if status < 0.5:
        title = 'Python 3 Wall of Shame'
    else:
        title = 'Python 3 Wall of Superpowers'
    
    template_values = {
        'title': title,
        'packages': packages_list,
        'count': "%d/%d" % (good, total),
        }
    return template_values


class DatabaseMainPage(webapp.RequestHandler):
    def get(self):
        template_values = build_data()
        path = os.path.join(os.path.dirname(__file__), 'index_db.html')
        self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication(
                                     [
                                     ('/fromhtml', MainPage),
                                     ('/', DatabaseMainPage),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
