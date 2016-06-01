
#from urllib.request import urlopen
import logging
from urllib import urlopen
import xmlrpclib
import pprint
import re
import os
import datetime
import traceback

import config

base_url = 'http://pypi.python.org'

how_many_to_chart = 200

is_app_engine = config.GAE


if is_app_engine:
    from google.appengine.api import urlfetch

    '''
    `set_default_fetch_deadline` to avoid the following errors:
    http://stackoverflow.com/questions/13051628/gae-appengine-deadlineexceedederror-deadline-exceeded-while-waiting-for-htt
    
    Failed to fetch http://pypi.python.org/pypi, caused by: Traceback (most recent call last):
    File "/base/data/home/apps/s~python3wos2/1.389386800936840076/pypi_parser.py", line 37, in request
        headers={'Content-Type': 'text/xml'})
    File "/base/data/home/runtimes/python/python_lib/versions/1/google/appengine/api/urlfetch.py", line 271, in fetch
        return rpc.get_result()
    File "/base/data/home/runtimes/python/python_lib/versions/1/google/appengine/api/apiproxy_stub_map.py", line 613, in get_result
        return self.__get_result_hook(self)
    File "/base/data/home/runtimes/python/python_lib/versions/1/google/appengine/api/urlfetch.py", line 428, in _get_fetch_result
        'Deadline exceeded while waiting for HTTP response from URL: ' + url)
    DeadlineExceededError: Deadline exceeded while waiting for HTTP response from URL: http://pypi.python.org/pypi
    '''
    urlfetch.set_default_fetch_deadline(60)
    
    class GAEXMLRPCTransport(object):
        """Handles an HTTP transaction to an XML-RPC server."""

        def __init__(self):
            pass

        def request(self, host, handler, request_body, verbose=0):
            result = None
            url = 'http://%s%s' % (host, handler)
            try:
                response = urlfetch.fetch(url,
                                          payload=request_body,
                                          method=urlfetch.POST,
                                          headers={'Content-Type': 'text/xml'})
            except Exception, e:
                msg = 'Failed to fetch %s, caused by: %s' % (url, traceback.format_exc())
                logging.error(msg)
                raise xmlrpclib.ProtocolError(host + handler, 500, msg, {})

            if response.status_code != 200:
                logging.error('%s returned status code %s' % 
                              (url, response.status_code))
                raise xmlrpclib.ProtocolError(host + handler,
                                              response.status_code,
                                              "",
                                              response.headers)
            else:
                result = self.__parse_response(response.content)

            return result

        def __parse_response(self, response_body):
            p, u = xmlrpclib.getparser(use_datetime=False)
            p.feed(response_body)
            return u.close()
        
    CLIENT = xmlrpclib.ServerProxy('http://pypi.python.org/pypi', GAEXMLRPCTransport())
else:
    CLIENT = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')

class NoReleasesException(Exception):
    pass

def get_package_info(name):
    # Having to `lower` the name is a new requirement as of somewhere beteen 2015-12 and 2016-05.
    # Strange.
    # Maybe we don't need to `lower`? I'm confused.
    safe_name = name
    release_list = CLIENT.package_releases(safe_name, True)
    
    downloads = 0
    py3 = False
    py2only = False
    url = 'http://pypi.python.org/pypi/' + safe_name
    most_recent = True

    if len(release_list) == 0:
        raise NoReleasesException("No releases or a pypi bug for: %s" % safe_name)

    for release in release_list:
        release_metadata = None
        for i in range(3):
            try:
                urls_metadata_list = CLIENT.release_urls(safe_name, release)
                release_metadata = CLIENT.release_data(safe_name, release)
                break
            except xmlrpclib.ProtocolError, e:
                # retry 3 times
                strace = traceback.format_exc()
                logging.error("retry %s xmlrpclib: %s" % (i, strace))

        if release_metadata is None:
            raise Exception("Failed to fetch release metadata for release: %s" % release)

        url = release_metadata['package_url']
        
        if most_recent:
            most_recent = False
            # to avoid checking for 3.1, 3.2 etc, lets just str the classifiers
            classifiers = str(release_metadata['classifiers'])
            if 'Programming Language :: Python :: 3' in classifiers:
                py3 = True
            elif 'Programming Language :: Python :: 2 :: Only' in classifiers:
                py2only = True
        
        for url_metadata in urls_metadata_list:
            downloads += url_metadata['downloads']

    # NOTE: packages with no releases or no url's just throw an exception.
    info = dict(
        py2only=py2only,
        py3=py3,
        downloads=downloads,
        name=name,
        url=url,
        timestamp=datetime.datetime.utcnow().isoformat(),
        )

    return info

if is_app_engine:
    def get_list_of_packages():
        return CLIENT.list_packages()
else:
    #from filecache import filecache
    #@filecache(24 * 60 * 60)
    def get_list_of_packages():
        return CLIENT.list_packages()

def get_packages():
    package_names = get_list_of_packages()
    
    exceptions = []
    for pkg in package_names:
        try:
            info = get_package_info(pkg)
        except Exception, e:
            print(pkg)
            print(e)
            exceptions.append(e)
            continue
            # raise exceptions later after you tried updating all of the packages.
            
        print info
        yield info
    
    for e in exceptions:
        raise e


def build_html(packages_list):
    total_html = '''<table><tr><th>Package</th><th>Downloads</th></tr>%s</table>'''
    rows = []
    row_template = '''<tr class="py3{py3}"><td><a href="{url}" timestamp="{timestamp}">{name}</a></td><td>{downloads}</td></tr>'''
    for package in reversed(packages_list):
        rows.append(row_template.format(**package))

    return total_html % '\n'.join(rows)


def count_good(packages_list):
    good = 0
    for package in packages_list:
        if package.py3:
            good += 1
    return good

def remove_irrelevant_packages(packages):
    to_ignore = 'multiprocessing', 'simplejson', 'argparse', 'uuid', 'setuptools'
    for pkg in packages:
        if pkg['name'] in to_ignore:
            continue
        else:
            yield pkg


def main():
    packages = get_packages()
    packages = remove_irrelevant_packages(packages)
    packages = list(packages)
    def get_downloads(x): return x['downloads']
    packages.sort(key=get_downloads)

    # just for backup
    open('results.txt', 'w').write(pprint.pformat(packages))

    top = packages[-how_many_to_chart:]
    html = build_html(top)

    open('results.html', 'w').write(html)
    
    open('count.txt', 'w').write('%d/%d' % (count_good(top), len(top)))
    open('date.txt', 'w').write(datetime.datetime.now().isoformat())

def test():
    print(get_package_info('Shinken'))
    
if __name__ == '__main__':
    #main()
    test()

    
