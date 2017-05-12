
from bxml import XML
from . import NS    

class Metadata(XML):
    ROOT_TAG = "{%(pub)s}metadata" % NS

    def identifier(self, id_patterns=['isbn']):
        identifier = None
        for pattern in id_patterns:
            identifier = self.find(self.root, "dc:identifier[contains(@id, '%s')]" % pattern, namespaces=NS)
            if identifier is not None: return identifier

    def element_text(self, xpath):
        return self.find(self.root, "%s/text()" % xpath, namespaces=NS)

    def meta_text(self, property_name):
        return self.element_text("opf:meta[@property='%s']" % property_name)

    @property
    def title_text(self):
        return self.element_text("dc:title")

    @property
    def publisher_text(self):
        return self.element_text("dc:publisher")

    @property
    def date_text(self):
        return self.element_text("dc:date")        

    @property
    def description_text(self):
        return self.element_text("dc:description")

    @property
    def rights(self):
        return self.element_text("dc:rights")

    @property
    def identifiers(self):
        return self.xpath(self.root, "dc:identifiers/text()", namespaces=NS)

    @property
    def identifiers_with_formats(self):
        entries = []
        for elem in self.xpath(self.root, "dc:identifier", namespaces=NS):
            entries.append(
                (elem.text or '', self.element_text("opf:meta[@refines='#%s']" % elem.get('id'))))
        return entries

    @property
    def creators(self):
        return self.xpath(self.root, "dc:creator/text()", namespaces=NS)

    @property
    def creators_with_roles(self):
        entries = []
        for elem in self.xpath(self.root, "dc:creator", namespaces=NS):
            entries.append(
                (elem.text or '', self.element_text("opf:meta[@refines='#%s']" % elem.get('id'))))
        return entries

    @property
    def contributors(self):
        return self.xpath(self.root, "dc:contributor/text()", namespaces=NS)

    @property
    def subjects(self):
        return self.xpath(self.root, "dc:subject/text()", namespaces=NS)

