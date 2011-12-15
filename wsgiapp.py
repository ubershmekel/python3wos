

import os

import webapp2
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import main
import pypi_cron

app = webapp2.WSGIApplication(
    [
        ('/', main.DatabaseMainPage),

        ('/tasks/update', pypi_cron.CronUpdate),
        ('/tasks/package_list', pypi_cron.PackageList),
        ('/tasks/erase_to_ignore', pypi_cron.EraseToIgnore),
        ('/tasks/erase_dups', pypi_cron.EraseDups),
        ('/tasks/clear_cache', pypi_cron.ClearCache),
        ('/tasks/update_models', pypi_cron.update_models),
    ],
    debug=True)


def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
