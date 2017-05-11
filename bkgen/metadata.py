
from bxml import XML
from . import NS    

class Metadata(XML):
    ROOT_TAG = "{%(pub)s}metadata" % NS

    def identifier(self, id_patterns=['isbn']):
        identifier = None
        for pattern in id_patterns:
            identifier = self.find(self.root, "dc:identifier[contains(@id, '%s')]" % pattern, namespaces=NS)
            if identifier is not None: return identifier
 
    @property
    def title_text(self):
        return self.find(self.root, "dc:title/text()", namespaces=NS)

    @property
    def description_text(self):
        return self.find(self.root, "dc:description/text()", namespaces=NS)

    def meta_text(self, property):
        return self.find(self.root, "opf:meta[@property='%s']/text()" % property, namespaces=NS)

    @property
    def creators(self):
        return self.xpath(self.root, "dc:creator/text()", namespaces=NS)

    @property
    def contributors(self):
        return self.xpath(self.root, "dc:contributor/text()", namespaces=NS)

