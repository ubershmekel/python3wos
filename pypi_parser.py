
#from urllib.request import urlopen
from urllib import urlopen
import xmlrpclib
import pprint
import re
import os
from collections import namedtuple
import datetime

from BeautifulSoup import BeautifulSoup

from filecache import filecache

base_url = 'http://pypi.python.org'
pkg_list_url = base_url + '/pypi?%3Aaction=index'
pkg_info = namedtuple('pkg_info', 'name url py3 downloads')

how_many_to_chart = 200

CLIENT = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
    
def get_package_info(name):
    release_list = CLIENT.package_releases(name, True)
    
    downloads = 0
    py3 = False
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
    info = pkg_info(py3=py3, downloads=downloads, name=name, url=url)

    return info

    
def get_packages():
    package_names = CLIENT.list_packages()
    
    
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
    row_template = '''<tr class="py3{py3}"><td><a href="{url}">{name}</a></td><td>{downloads}</td></tr>'''
    for package in reversed(packages_list):
        rows.append(row_template.format(**package._asdict()))

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
        if pkg.name in to_ignore:
            continue
        else:
            yield pkg


def main():
    packages = get_packages()
    packages = remove_irrelevant_packages(packages)
    packages = list(packages)
    def get_downloads(x): return x.downloads
    packages.sort(key=get_downloads)

    # just for backup
    open('results.txt', 'w').write(pprint.pformat(packages))

    top = packages[-how_many_to_chart:]
    html = build_html(top)

    open('results.html', 'w').write(html)
    
    open('count.txt', 'w').write('%d/%d' % (count_good(top), len(top)))
    open('date.txt', 'w').write(datetime.datetime.now().isoformat())
    

main()

    
