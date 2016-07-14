

import os

#import webapp2
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import main
import pypi_cron

app = webapp.WSGIApplication(
    [
        ('/', main.DatabaseMainPage),

        ('/tasks/update_top', pypi_cron.CronUpdateTop),
        ('/tasks/clear_cache', pypi_cron.ClearCache),
    ],
    debug=True)


def main():
    run_wsgi_app(app)

    
if __name__ == "__main__":
    main()
