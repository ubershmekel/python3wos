import cPickle
import zlib
import datetime
import traceback
import logging

from google.appengine.ext import webapp
from google.appengine.api import memcache

import pypi_parser


PACKAGES_CACHE_KEY = 'packages_names'


def compress_and_store(obj, key):
    # The maximum size of a cached data value is 1 MB (10^6 bytes).
    compressed_bytes = zlib.compress(cPickle.dumps(obj))
    memcache.add(key, compressed_bytes, 60 * 60 * 24)


def get_and_decompress(key):
    compressed_bytes = memcache.get(key)
    if compressed_bytes is None:
        # for handling the empty cache
        return None
    return cPickle.loads(zlib.decompress(compressed_bytes))


def fetch_and_cache_package_info():
    packages = list(pypi_parser.get_packages())
    compress_and_store(packages, PACKAGES_CACHE_KEY)
    return packages


def get_packages_list_from_cache_or_pypi():
    packages = get_and_decompress(PACKAGES_CACHE_KEY)
    if packages is None:
        return fetch_and_cache_package_info()
    else:
        return packages

def update_handler(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('\r\n')

    try:
        fetch_and_cache_package_info()
    except Exception, e:
        self.response.out.write(" - %s" % e)
        strace = traceback.format_exc()
        self.response.out.write(strace)

    self.response.out.write("\r\n")

class CronUpdateTop(webapp.RequestHandler):
    def get(self):
        update_handler(self)


class ClearCache(webapp.RequestHandler):
    def get(self):
        from google.appengine.api import memcache
        from config import HTML_CACHE_KEY
        self.response.out.write("clearing cache")
        result = memcache.delete(HTML_CACHE_KEY)
        self.response.out.write("result: %s" % result)


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
