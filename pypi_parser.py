
#from urllib.request import urlopen
from urllib import urlopen
import xmlrpclib
import pprint
import re
import os
import datetime


base_url = 'http://pypi.python.org'
pkg_list_url = base_url + '/pypi?%3Aaction=index'

how_many_to_chart = 200

is_app_engine = os.environ['SERVER_SOFTWARE'].startswith('Development') or os.environ['SERVER_SOFTWARE'].startswith('Google')

if is_app_engine:
    from google.appengine.api import urlfetch

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
            except:
                msg = 'Failed to fetch %s' % url
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


def get_package_info(name):
    release_list = CLIENT.package_releases(name, True)
    
    downloads = 0
    py3 = False
    url = 'http://pypi.python.org/pypi/' + name
    for release in release_list:
        urls_metadata_list = CLIENT.release_urls(name, release)
        release_metadata = CLIENT.release_data(name, release)
        url = release_metadata['package_url']
        
        for url_metadata in urls_metadata_list:
            downloads += url_metadata['downloads']
            # to avoid checking for 3.1, 3.2 etc, lets just str the classifiers
            if 'Programming Language :: Python :: 3' in str(release_metadata['classifiers']):
                py3 = True

    # NOTE: packages with no releases or no url's just throw an exception.
    info = dict(py3=py3, downloads=downloads, name=name, url=url, timestamp=datetime.datetime.utcnow().isoformat())

    return info

if is_app_engine:
    def get_list_of_packages():
        return CLIENT.list_packages()
else:
    from filecache import filecache
    @filecache(24 * 60 * 60)
    def get_list_of_packages():
        return CLIENT.list_packages()

def get_packages():
    package_names = get_list_of_packages()
    
    for pkg in package_names:
        try:
            info = get_package_info(pkg)
        except Exception, e:
            print(pkg)
            print(e)
            continue
            
        print info
        yield info


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
    
if __name__ == '__main__':
    main()

    
