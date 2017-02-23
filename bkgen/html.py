
from bxml import XML
from bkgen import NS

class HTML(XML):
    ROOT_TAG = "{%(html)s}html" % NS

