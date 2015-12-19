import pprint
import datetime

import pypi_parser

info = pypi_parser.get_package_info('requests')
info['timestamp'] = datetime.datetime.utcnow()
#for key, value in info.items():
#	setattr(pkg, key, value)
#fix_equivalence(pkg)

print(info)
pprint.pprint(info.items())