
from bxml import XML
from pubxml import NS

class HTML(XML):
    ROOT_TAG = "{%(html)s}html" % NS

