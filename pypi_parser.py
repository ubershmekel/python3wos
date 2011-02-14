
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

how_many_to_chart = 100


@filecache(3 * 24 * 60 * 60)
def get_page(url):
    return urlopen(url).read()


def get_rows():
    html = get_page(pkg_list_url)
    rows = re.findall(b'<tr[ ].*?</tr>', html, re.DOTALL)
    return rows


def get_url(row):
    return re.findall(r'href="([^"]+)', row)[0]

    
def get_table(html, table_index=0):
    soup = BeautifulSoup(html)
    table = []
    all_tables = soup.findAll('table')
    if len(all_tables) == 0:
        return
    table_soup = all_tables[table_index]
    for tr in table_soup.findAll('tr'):
        row = []
        for td in tr.findAll(['td', 'th']):
            row.append(''.join(td.findAll(text=True)).strip())
        table.append(row)

    return table

    
def get_downloads(html):
    downloads = 0
    
    # only one specific, table contains the downloads count
    table_id = '''<table class="list" style="margin-bottom: 10px;">'''
    downloads_table_html_found = re.findall(re.escape(table_id) + r'.*?</table>', html, re.DOTALL)
    
    if len(downloads_table_html_found) == 0:
        return 0
    
    table = get_table(downloads_table_html_found[0])
    if table is None:
        return 0
    
    for row in table:
        if len(row) == 0:
            continue
        downloads_column = row[-1]
        if downloads_column.isdigit():
            downloads += int(downloads_column)

    return downloads

client = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')

@filecache(3 * 24 * 60 * 60)
def get_package_info(name):
    release_list = client.package_releases(name, True)
    
    downloads = 0
    py3 = False
    for release in release_list:
        urls_metadata_list = client.release_urls(name, release)
        release_metadata = client.release_data(name, release)
        url = release_metadata['package_url']
        
        for url_metadata in urls_metadata_list:
            downloads += url_metadata['downloads']
            if 'Programming Language :: Python :: 3' in release_metadata['classifiers']:
                py3 = True
    

    info = pkg_info(py3=py3, downloads=downloads, name=name, url=url)

    return info

    
def get_packages():
    package_names = client.list_packages()
    
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


def remove_version_number(pkg_name):
    return re.findall(r'^(.*) [^ ]+$', pkg_name)[0]
    
def remove_version_number_url(url):
    return re.findall(r'^(.*)/[^/]+$', url)[0]

def remove_irrelevant_packages(packages):
    to_ignore = 'multiprocessing', 'simplejson', 'argparse', 'uuid'
    for pkg in packages:
        # get the package name assuming the version number has no spaces in it
        #name_no_ver = remove_version_number(pkg.name)
        #if name_no_ver in to_ignore:
        if pkg.name in to_ignore:
            continue
        else:
            yield pkg

def aggregate_multiple_versions(packages):
    unique_packages = {}
    for pkg in packages:
        new_name = remove_version_number(pkg.name)
        new_url = remove_version_number_url(pkg.url)
        # pkg is an immutable tuple so you need to make a new instance
        pkg = pkg._replace(name=new_name, url=new_url)
        if pkg.name in unique_packages:
            old_pkg = unique_packages[pkg.name]
            new_downloads = old_pkg.downloads + pkg.downloads
            unique_packages[pkg.name] = old_pkg._replace(downloads=new_downloads)
        else:
            unique_packages[pkg.name] = pkg
    
    return unique_packages.values()
        

def main():
    packages = get_packages()
    packages = remove_irrelevant_packages(packages)
    #packages = remove_irrelevant_packages(packages)
    #packages = aggregate_multiple_versions(packages)
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

    
