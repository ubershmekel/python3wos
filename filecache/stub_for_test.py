
import time
from filecache import filecache

@filecache(30)
def the_time():
    return time.time()
