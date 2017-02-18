
from bxml import XML
from . import NS    

class Metadata(XML):
    ROOT_TAG = "{%(pub)s}metadata" % NS
