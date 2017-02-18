
from bl.dict import Dict
from bxml import XML
from . import NS    

class Document(XML):
    ROOT_TAG = "{%(pub)s}document" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'pub', 'epub']})
