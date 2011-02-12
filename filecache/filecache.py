'''
filecache

filecache is a decorator which saves the return value of functions even
after the interpreter dies. For example this is useful on functions that download
and parse webpages for example. All you need to do is specify for how long
the return values should be cached (use seconds, like time.sleep).

USAGE:

from filecache import filecache

@filecache(24 * 60 * 60)
def time_consuming_function(args):
    # etc


NOTE: All arguments of the decorated function and the return value need to be
    picklable for this to work.

NOTE: The cache isn't automatically cleaned, it is only overwritten. If your
    function can receive many different arguments that rarely repeat, your
    cache may forever grow. One day I might add a feature that once in every
    100validity scans the db for outdated stuff and erases.

Tested on python 2.7 and 3.1

License: BSD, do what you wish with this. Could be awesome to hear if you found
it useful and/or you have suggestions. ubershmekel at gmail

'''


import time as _time
import shelve as _shelve
import pickle as _pickle
import functools as _functools
import inspect as _inspect
import collections as _collections
import sys as _sys

__retval = _collections.namedtuple('__retval', 'timesig data')

def __get_cache_name(function):
    module_name = _inspect.getfile(function)
    return module_name + '.cache'
                   
def filecache(seconds_of_validity):
    '''
    filecache is called and the decorator should be returned.
    '''
    def filecache_decorator(function):
        @_functools.wraps(function)
        def function_with_cache(*args, **kwargs):
            arguments = (args, kwargs)

            # make sure cache is loaded
            if not hasattr(function, '__db'):
                function.__db = _shelve.open(__get_cache_name(function))

            # Check if you have a valid, cached answer, and return it.
            # Sadly this is python version dependant
            if _sys.version_info[0] == 2:
                key = function.__name__ + _pickle.dumps(arguments)
            else:
                # NOTE: protocol=0 so it's ascii, this is crucial for py3k
                #       because shelve only works with proper strings.
                #       Otherwise, we'd get an exception because
                #       function.__name__ is str but dumps returns bytes.
                key = function.__name__ + _pickle.dumps(arguments, protocol=0).decode('ascii')
                
            if key in function.__db:
                rv = function.__db[key]
                if _time.time() - rv.timesig < seconds_of_validity:
                    return _pickle.loads(rv.data)

            retval = function(*args, **kwargs)

            # store in cache
            # NOTE: no need to __db.sync() because there was no mutation
            function.__db[key] = __retval(_time.time(), _pickle.dumps(retval))
            
            return retval

        return function_with_cache

    return filecache_decorator



