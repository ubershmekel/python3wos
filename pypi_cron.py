import os
import datetime

import cgi
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import pypi_parser

from PypiPackage import Package

TO_IGNORE = 'multiprocessing', 'simplejson', 'argparse', 'uuid', 'setuptools', 'Jinja'

def update_list_of_packages():
    package_names = pypi_parser.get_list_of_packages()

    for name in package_names:
        if name in TO_IGNORE:
            continue
        query = db.GqlQuery("SELECT * FROM Package WHERE name = :name", name=name)
        if len(list(query)) == 0:
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


class EraseDups(webapp.RequestHandler):
    def get(self):
        packages = db.GqlQuery("SELECT * FROM Package")
        done_already = set()
        for pkg in packages:
            if pkg.name in done_already:
                continue
            query = db.GqlQuery("SELECT * FROM Package WHERE name = :name", name=pkg.name)
            dups = list(query)
            if len(dups) > 1:
                self.response.out.write(pkg.name + '\r\n')
                best_item = dups[0]
                best_i = 0
                for i, item in enumerate(dups):
                    if best_item < item.timestamp:
                        best_i = i
                        best_item = item
                    for i in range(len(dups)):
                        if i != best_i:
                            dups[i].delete()
            done_already.add(pkg.name)

class ClearCache(webapp.RequestHandler):
    def get(self):
        from google.appengine.api import memcache
        from python3wos import HTML_CACHE_KEY
        self.response.out.write("clearing cache")
        result = memcache.delete(HTML_CACHE_KEY)
        self.response.out.write("result: %s" % result)

application = webapp.WSGIApplication(
                                     [
                                     ('/tasks/update', CronUpdate),
                                     ('/tasks/package_list', PackageList),
                                     ('/tasks/erase_to_ignore', EraseToIgnore),
                                     ('/tasks/erase_dups', EraseDups),
                                     ('/tasks/clear_cache', ClearCache),
                                      ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
