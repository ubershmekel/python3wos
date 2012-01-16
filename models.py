from google.appengine.ext import db

class Package(db.Model):
    name = db.StringProperty(multiline=False)
    url = db.StringProperty(multiline=False)
    timestamp = db.DateTimeProperty(auto_now_add=False)
    py3 = db.BooleanProperty()
    downloads = db.IntegerProperty()
    equivalent_url = db.StringProperty(multiline=False)
    py2only = db.BooleanProperty()
    force_green = db.BooleanProperty()

    def __str__(self):
        data = []
        for key in self.fields().keys():
            val = getattr(self, key)
            data.append('%s: %s' % (key, repr(val)))
            
        return '<br/>'.join(data)
