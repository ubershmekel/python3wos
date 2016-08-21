
import json
import logging
from urllib import urlopen
import xmlrpclib
import pprint
import re
import os
import datetime
import traceback

from easydict import EasyDict

import config

PYPI_URL = 'https://pypi.python.org/pypi'
PACKAGE_INFO_FMT = '{package_index_url}/{package}/json'

HOW_MANY_TO_CHART = 200


FORCE_GREEN = set([
    'zc.recipe.egg',
    'bcdoc',
])

EQUIVALENTS = {
    'argparse': 'https://docs.python.org/3/library/argparse.html',
    'BeautifulSoup': 'http://pypi.python.org/pypi/beautifulsoup4/',
    'dnspython': 'http://pypi.python.org/pypi/dnspython3',
    'Fabric': 'https://pypi.python.org/pypi/Fabric3',
    'functools32': 'https://docs.python.org/3/library/functools.html',
    'futures': 'http://docs.python.org/3/library/concurrent.futures.html',
    'ipaddr': 'https://docs.python.org/3/library/ipaddress.html',
    'ipaddress': 'https://docs.python.org/3/library/ipaddress.html',
    'MySQL-python': 'https://pypi.python.org/pypi/mysqlclient',
    'multiprocessing': 'https://docs.python.org/3/library/multiprocessing.html',
    'ordereddict': 'http://docs.python.org/3/library/collections.html#collections.OrderedDict',
    'python-memcached': 'https://pypi.python.org/pypi/python3-memcached',
    'python-openid': 'https://github.com/necaris/python3-openid',
    'simplejson': 'https://docs.python.org/3/library/json.html',
    'suds': 'https://pypi.python.org/pypi/suds-jurko',
    'ssl': 'http://docs.python.org/3/library/ssl.html',
    'unittest2': 'https://docs.python.org/3/library/unittest.html',
    'uuid': 'https://docs.python.org/3/library/uuid.html',
    'xlwt': 'https://pypi.python.org/pypi/xlwt-future',
}


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
            url = 'https://%s%s' % (host, handler)
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
        
    CLIENT = xmlrpclib.ServerProxy(PYPI_URL, GAEXMLRPCTransport())
else:
    CLIENT = xmlrpclib.ServerProxy(PYPI_URL)

class NoReleasesException(Exception):
    pass

def fix_equivalence(pkg):
    if pkg.name in EQUIVALENTS:
        pkg.equivalent_url = EQUIVALENTS[pkg.name]
    else:
        pkg.equivalent_url = None
    if pkg.name in FORCE_GREEN:
        pkg.force_green = True
    else:
        pkg.force_green = False

def get_package_info(name, downloads=0):
    metadata_url = PACKAGE_INFO_FMT.format(package_index_url=PYPI_URL, package=name)
    print(metadata_url)
    package_data_str = urlopen(metadata_url).read()
    package_data = json.loads(package_data_str)
    py3 = False
    py2only = False
    url = package_data.get('package_url', PYPI_URL + '/' + name)

    release_list = package_data["releases"]
    if len(release_list) == 0:
        # NOTE: packages with no releases or no url's just throw an exception.
        raise NoReleasesException("No releases or a pypi bug for: %s" % name)

    # str(list) so we can easily find Python 3.X classifiers
    classifiers = str(package_data["info"]['classifiers'])
    if 'Programming Language :: Python :: 3' in classifiers:
        py3 = True
    elif 'Programming Language :: Python :: 2 :: Only' in classifiers:
        py2only = True

    info = EasyDict(
        py2only=py2only,
        py3=py3,
        downloads=downloads,
        name=name,
        url=url,
        timestamp=datetime.datetime.utcnow().isoformat(),
        )

    fix_equivalence(info)
    return info

def get_packages():
    package_name_downloads = CLIENT.top_packages(HOW_MANY_TO_CHART)
    
    exceptions = []
    for pkg_name, downloads in package_name_downloads:
        print(pkg_name, downloads)
        try:
            info = get_package_info(pkg_name, downloads=downloads)
        except Exception, e:
            print(pkg_name)
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


def main():
    packages = get_packages()
    packages = list(packages)
    def get_downloads(x): return x['downloads']
    packages.sort(key=get_downloads)

    top = packages[-HOW_MANY_TO_CHART:]
    html = build_html(top)

    html_fname = 'results.html'
    open(html_fname, 'w').write(html)
    import webbrowser
    webbrowser.open(html_fname)

def test():
    print(get_package_info('coverage'))
    
if __name__ == '__main__':
    #main()
    test()

    
