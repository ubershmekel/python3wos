

import unittest
import imp
import time
import random
import os

from filecache import filecache
from filecache import __get_cache_name as gcn

class TestFilecache(unittest.TestCase):
    def setUp(self):
        shelve_suffixes = ('.cache', '.cache.bak', '.cache.dir', '.cache.dat')
        # os.listdir doesn't accept an empty string but dirname returns ''
        here = os.path.dirname(__file__) or '.'
        fname_list = os.listdir(here)
        
        for fname in fname_list:
            if fname.endswith(shelve_suffixes):
                os.remove(fname)
    
    def test_returns(self):
        # make sure the thing works
        @filecache(30)
        def donothing(x):
            return x

        params = [1, 'a', 'asdfa', set([1,2,3])]
        for item in params:
            self.assertEqual(donothing(item), item)
        
    def test_speeds(self):
        DELAY = 0.5
        @filecache(30)
        def waiter(x):
            time.sleep(DELAY)
            return x

        start = time.time()
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        self.assertEqual(waiter(123), 123)
        finish = time.time()

        # ran it 4 times but it should run faster than DELAY * 4
        self.assertTrue(finish - start < (DELAY * 2))

    def test_invalidates(self):
        wait = 0.1
        items = [1337, 69]
        
        @filecache(wait)
        def popper():
            return items.pop()

        first = popper()
        # I would wait just for it exactly but time.time() isn't accurate enough.
        time.sleep(wait * 1.1)
        second = popper()
        
        self.assertNotEqual(first, second)

    def test_works_after_reload(self):
        import stub_for_test
        first = stub_for_test.the_time()
        # sleep a bit because time.time() == time.time()
        time.sleep(0.1)
        imp.reload(stub_for_test)
        second = stub_for_test.the_time()
        self.assertEqual(first, second)

if __name__ == '__main__':
    unittest.main()

