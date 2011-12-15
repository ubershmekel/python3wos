import os


HTML_CACHE_KEY = "WOShtml"


DEV = False
LIVE = False

if os.environ['SERVER_SOFTWARE'].startswith('Google'):
    # remote google apps
    LIVE = True
elif os.environ['SERVER_SOFTWARE'].startswith('Development'):
    # local dev server
    # True sometimes works
    DEV = True

GAE = LIVE or DEV

