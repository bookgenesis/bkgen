
from bxml import XML
from . import NS    

class Metadata(XML):
    ROOT_TAG = "{%(pub)s}metadata" % NS

    def get_dc_identifier(self, id_patterns=['isbn']):
        identifier = None
        for pattern in id_patterns:
            identifier = self.find(self.root, "dc:identifier[contains(@id, '%s')]" % pattern, namespaces=NS)
            if identifier is not None: return identifier
 
