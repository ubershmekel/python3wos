import os
from google.appengine.ext.webapp import template
import cgi
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail

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



application = webapp.WSGIApplication(
                                     [
                                     ('/', MainPage),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
