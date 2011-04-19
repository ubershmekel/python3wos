from google.appengine.ext import db

class Package(db.Model):
    name = db.StringProperty(multiline=False)
    url = db.StringProperty(multiline=False)
    timestamp = db.DateTimeProperty(auto_now_add=False)
    py3 = db.BooleanProperty()
    downloads = db.IntegerProperty()

