import os
import datetime
import traceback

import webapp2
#from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import pypi_parser
from models import Package
import config

UPDATE_AT_A_TIME = 10

if config.DEV:
    # faster when developing
    UPDATE_AT_A_TIME = 2


#TO_IGNORE = 'multiprocessing', 'simplejson', 'argparse', 'uuid', 'setuptools', 'Jinja', 'unittest2'
EQUIVALENTS = {
    'multiprocessing': 'http://docs.python.org/py3k/library/multiprocessing.html',
    'argparse': 'http://docs.python.org/py3k/library/argparse.html',
    'uuid': 'http://docs.python.org/py3k/library/uuid.html',
    'unittest2': 'http://docs.python.org/py3k/library/unittest.html',
    'simplejson': 'http://docs.python.org/py3k/library/json.html',
    }

# the following have a dup on the list
# setuptools - distribute
# Jinja - jinja2
TO_IGNORE = 'setuptools', 'Jinja', 


def fix_equivalence(pkg):
    pkg.equivalent_url = EQUIVALENTS.get(name, '')    


def update_list_of_packages():
    package_names = pypi_parser.get_list_of_packages()

    for name in package_names:
        if name in TO_IGNORE:
            continue
        query = db.GqlQuery("SELECT * FROM Package WHERE name = :name", name=name)
        if len(list(query)) == 0:
            p = Package(name=name)
            p.put()
        

class CronUpdate(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('\r\n')
        # get outdated package infos
        packages = db.GqlQuery("SELECT * FROM Package ORDER BY timestamp ASC LIMIT %d" % UPDATE_AT_A_TIME)

        packages_list = list(packages)
        if len(packages_list) == 0:
            update_list_of_packages()

        for pkg in packages_list:
            self.response.out.write(pkg.name)
            try:
                info = pypi_parser.get_package_info(pkg.name)
            except Exception, e:
                self.response.out.write(" - %s" % e)
                strace = traceback.format_exc()
                self.response.out.write(strace)
            else:
                info_dict = info
                info_dict['timestamp'] = datetime.datetime.utcnow()
                for key, value in info_dict.items():
                    setattr(pkg, key, value)
                fix_equivalence(pkg)
                pkg.put()
            
            self.response.out.write("\r\n")
            

class PackageList(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("updating package list")

        # get outdated package infos
        update_list_of_packages()

class EraseToIgnore(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("erasing packages")
        for name in TO_IGNORE:
            packages = db.GqlQuery("SELECT * FROM Package WHERE name = :1", name)
            for pkg in packages:
                pkg.delete()


class EraseDups(webapp2.RequestHandler):
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

class ClearCache(webapp2.RequestHandler):
    def get(self):
        from google.appengine.api import memcache
        from main import HTML_CACHE_KEY
        self.response.out.write("clearing cache")
        result = memcache.delete(HTML_CACHE_KEY)
        self.response.out.write("result: %s" % result)


# Request handler for the URL /update_datastore
class update_models(webapp2.RequestHandler):
    def get(self):
        import urllib
        from google.appengine.ext.webapp import template
        url_n_template = 'update_models'
        name = self.request.get('name', None)
        if name is None:
            # First request, just get the first name out of the datastore.
            pkg = Package.gql('ORDER BY name DESC').get()
            name = pkg.name

        q = Package.gql('WHERE name <= :1 ORDER BY name DESC', name)
        items = q.fetch(limit=400)
        if len(items) > 1:
            next_name = items[-1].name
            next_url = '/tasks/%s?name=%s' % (url_n_template, urllib.quote(next_name))
        else:
            next_name = 'FINISHED'
            next_url = ''  # Finished processing, go back to main page.
        
        for current_pkg in items:
            # modify the model if needed here
            fix_equivalence(current_pkg)
            
            current_pkg.py2only = False
            current_pkg.put()

        context = {
            'current_name': name,
            'next_name': next_name,
            'next_url': next_url,
        }
        self.response.out.write(template.render('%s.html' % url_n_template, context))

