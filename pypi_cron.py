import os
import datetime

import cgi
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import pypi_parser

from PypiPackage import Package

TO_IGNORE = 'multiprocessing', 'simplejson', 'argparse', 'uuid', 'setuptools'

def update_list_of_packages():
    package_names = pypi_parser.get_list_of_packages()

    for name in package_names:
        if name in TO_IGNORE:
            continue
        query = db.GqlQuery("SELECT * FROM Package WHERE name = :name", name=name)
        if query.count() == 0:
            p = Package(name=name)
            p.put()
        

class CronUpdate(webapp.RequestHandler):
    def get(self):
        self.response.out.write("@")
        
        # get outdated package infos
        packages = db.GqlQuery("SELECT * FROM Package ORDER BY timestamp ASC LIMIT 10")

        packages_list = list(packages)
        if len(packages_list) == 0:
            update_list_of_packages()

        for pkg in packages_list:
            try:
                self.response.out.write(".")
                info = pypi_parser.get_package_info(pkg.name)
            except Exception, e:
                self.response.out.write("-")
                print(pkg)
                print(e)
                continue
                
            info_dict = info
            info_dict['timestamp'] = datetime.datetime.utcnow()
            for key, value in info_dict.items():
                setattr(pkg, key, value)
            pkg.put()
            

class PackageList(webapp.RequestHandler):
    def get(self):
        self.response.out.write("updating package list")

        # get outdated package infos
        update_list_of_packages()

class EraseToIgnore(webapp.RequestHandler):
    def get(self):
        self.response.out.write("erasing packages")
        for name in TO_IGNORE:
            packages = db.GqlQuery("SELECT * FROM Package WHERE name = :1", name)
            for pkg in packages:
                pkg.delete()




application = webapp.WSGIApplication(
                                     [
                                     ('/tasks/update', CronUpdate),
                                     ('/tasks/package_list', PackageList),
                                     ('/tasks/erase_to_ignore', EraseToIgnore),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
