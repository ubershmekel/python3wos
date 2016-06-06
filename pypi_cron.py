import cPickle
import zlib
import datetime
import traceback

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import memcache

import pypi_parser
from models import Package
import config

UPDATE_AT_A_TIME = 10

if config.DEV:
    # faster when developing
    UPDATE_AT_A_TIME = 2


DB_STEPS = 400

#TO_IGNORE = 'multiprocessing', 'simplejson', 'argparse', 'uuid', 'setuptools', 'Jinja', 'unittest2'
EQUIVALENTS = {
    'multiprocessing': 'https://docs.python.org/3/library/multiprocessing.html',
    'argparse': 'https://docs.python.org/3/library/argparse.html',
    'uuid': 'https://docs.python.org/3/library/uuid.html',
    'unittest2': 'https://docs.python.org/3/library/unittest.html',
    'simplejson': 'https://docs.python.org/3/library/json.html',
    'futures': 'http://docs.python.org/3/library/concurrent.futures.html',
    'ipaddr': 'https://docs.python.org/3/library/ipaddress.html',
    'MySQL-python': 'https://pypi.python.org/pypi/mysqlclient',
    'python-openid': 'https://github.com/necaris/python3-openid',
    'suds': 'https://pypi.python.org/pypi/suds-jurko',
    }

# the following have a dup on the list
# setuptools - distribute
# Jinja - jinja2
TO_IGNORE = 'setuptools', 'Jinja', 


def fix_equivalence(pkg):
    if pkg.name in EQUIVALENTS:
        pkg.equivalent_url = EQUIVALENTS[pkg.name]


PACKAGES_CACHE_KEY = 'packages_names'
PACKAGES_CHECKED_INDEX = 'packages_index'

def compress(obj):
    return zlib.compress(cPickle.dumps(obj))

def decompress(compressed_bytes):
    return cPickle.loads(zlib.decompress(compressed_bytes))

def get_mcache_package_list():
    buffer = memcache.get(PACKAGES_CACHE_KEY)
    if buffer is None:
        # for handling the empty cache
        return None
    if type(buffer) == list:
        # for migrating the existing memcache
        return buffer
    # normal flow
    return decompress(buffer)

def set_mcache_package_list(package_names):
    compressed_bytes = compress(package_names)
    memcache.add(PACKAGES_CACHE_KEY, compressed_bytes, 60 * 60 * 24)

def update_list_of_packages():
    package_names = get_mcache_package_list()
    package_index = memcache.get(PACKAGES_CHECKED_INDEX)

    if package_index is None:
        package_index = 0
    
    if package_names is None:
        package_names = pypi_parser.get_list_of_packages()
        set_mcache_package_list(package_names)

    for name in package_names[package_index:package_index + DB_STEPS]:
        if name in TO_IGNORE:
            pass
        else:
            query = db.GqlQuery("SELECT __key__ FROM Package WHERE name = :name", name=name)
            if len(list(query)) == 0:
                p = Package(name=name)
                p.put()
        
        package_index += 1
        if package_index % 5 == 0:
            memcache.set(PACKAGES_CHECKED_INDEX, package_index, 60 * 60 * 24)
            
    if package_index == len(package_names):
        return -1
    
    return package_index

def update_package_info(pkg):
    try:
        info = pypi_parser.get_package_info(pkg.name)
    except pypi_parser.NoReleasesException, e:
        print(pkg)
        print(e)
        # If this happens because of a pypi bug - we might want to consider doing something more serious here
        # TODO: figure this out better
        info = {}
    info['timestamp'] = datetime.datetime.utcnow()
    for key, value in info.items():
        setattr(pkg, key, value)
    fix_equivalence(pkg)
    pkg.put()
    return pkg

def update_handler(self, packages):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('\r\n')

    packages_list = list(packages)
    if len(packages_list) == 0:
        update_list_of_packages()

    for pkg in packages_list:
        self.response.out.write(pkg.name)
        try:
            update_package_info(pkg)
        except Exception, e:
            self.response.out.write(" - %s" % e)
            strace = traceback.format_exc()
            self.response.out.write(strace)

        self.response.out.write("\r\n")


class CronUpdate(webapp.RequestHandler):
    def get(self):
        # get outdated package infos
        packages = db.GqlQuery("SELECT * FROM Package ORDER BY timestamp ASC LIMIT %d" % UPDATE_AT_A_TIME)
        update_handler(self, packages)

class CronUpdateTop(webapp.RequestHandler):
    def get(self):
        query = "SELECT * FROM Package ORDER BY downloads DESC LIMIT 250"
        packages = list(db.GqlQuery(query))
        packages = sorted(packages, key=lambda x: x.timestamp)[:UPDATE_AT_A_TIME]
        #timestamp ASC LIMIT %d""" % UPDATE_AT_A_TIME
        update_handler(self, packages)

class PackageList(webapp.RequestHandler):
    def get(self):
        from google.appengine.ext.webapp import template
        #self.response.out.write("updating package list")
        # get outdated package infos
        i = update_list_of_packages()
        self.response.out.write("%d" % i)
        if i == -1:
            next_url = ''
        else:
            next_url = '#'
        context = {
            'title': 'Updating package list',
            'current_name': str(i),
            'next_name': str(i + DB_STEPS),
            'next_url': next_url,
        }
        self.response.out.write(template.render('redirect.html', context))

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
        from config import HTML_CACHE_KEY
        self.response.out.write("clearing cache")
        result = memcache.delete(HTML_CACHE_KEY)
        self.response.out.write("result: %s" % result)


# Request handler for the URL /update_datastore
class update_models(webapp.RequestHandler):
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
        items = q.fetch(limit=DB_STEPS)
        if len(items) > 1:
            next_name = items[-1].name
            next_url = '/tasks/%s?name=%s' % (url_n_template, urllib.quote(next_name))
        else:
            next_name = 'FINISHED'
            next_url = ''  # Finished processing, go back to main page.
        
        for current_pkg in items:
            # modify the model if needed here
            #fix_equivalence(current_pkg)
            #current_pkg.py2only = False
            
            if current_pkg.name in ('pylint', 'docutils'):
                current_pkg.force_green = True
            else:
                current_pkg.force_green = False
            current_pkg.put()
            # end of modify models

        context = {
            'current_name': name,
            'next_name': next_name,
            'next_url': next_url,
        }
        self.response.out.write(template.render('%s.html' % url_n_template, context))

class update_single(webapp.RequestHandler):
    def get(self):
        name = self.request.get('name', None)
        q = Package.gql('WHERE name = :1', name)
        items = q.fetch(limit=1)
        if len(items) == 0:
            self.response.out.write('did not find "%s"' % name)
            return
        pkg = items[0]
        pkg = update_package_info(pkg)
        self.response.out.write(str(pkg))

        

def profile_main():
    '''
    To profile a function, assign a function to "to_profile_func".
    
    NOTE:  This isn't working for some reason...
    '''
    import cProfile, pstats, StringIO
    prof = cProfile.Profile()
    prof = prof.runctx("to_profile_func()", globals(), locals())
    stream = StringIO.StringIO()
    stats = pstats.Stats(prof, stream=stream)
    stats.sort_stats("time")  # Or cumulative
    stats.print_stats(80)  # 80 = how many to print
    # The rest is optional.
    # stats.print_callees()
    # stats.print_callers()
    logging.info("Profile data:\n%s", stream.getvalue())

    
to_profile_func = None
#to_profile_func = update_list_of_packages

if to_profile_func is not None:
    to_profile_str = to_profile_func.__name__
    globals()[to_profile_str] = profile_main
