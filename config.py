import os


HTML_CACHE_KEY = "WOShtml"
PACKAGES_CACHE_KEY = "Packages"


DEV = False
LIVE = False

SERVER_SOFTWARE = 'SERVER_SOFTWARE'

if SERVER_SOFTWARE in os.environ:
    if os.environ[SERVER_SOFTWARE].startswith('Google'):
        # remote google apps
        LIVE = True
    elif os.environ[SERVER_SOFTWARE].startswith('Development'):
        # local dev server
        # True sometimes works
        DEV = True

GAE = LIVE or DEV

