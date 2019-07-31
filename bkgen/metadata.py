from bl.dict import Dict
from lxml import etree
from bxml import XML
from . import NS


class Metadata(XML):
    ROOT_TAG = "{%(opf)s}metadata" % NS
    NS = Dict(**{k: NS[k] for k in NS if k in ['opf', 'dc', 'dcterms', 'dcmitype', 'cp', 'xsi']})

    def identifier(self, id_patterns=['isbn']):
        identifier = None
        for pattern in id_patterns:
            identifier = self.find(self.root, "dc:identifier[contains(@id, '%s')]" % pattern)
            if identifier is not None:
                return identifier

    def meta(self, property_name):
        return self.element("opf:meta", property=property_name)

    @property
    def title(self):
        return self.element("dc:title")

    @property
    def publisher(self):
        return self.element("dc:publisher")

    @property
    def date(self):
        return self.element("dc:date")

    @property
    def description(self):
        return self.element("dc:description")

    @property
    def rights(self):
        return self.element("dc:rights")

    @property
    def identifiers(self):
        return self.xpath(self.root, "dc:identifier")

    @property
    def identifiers_with_formats(self):
        entries = []
        for elem in self.xpath(self.root, "dc:identifier"):
            entries.append(
                (
                    elem.text or '',
                    self.element("opf:meta", refines='#%s' % elem.get('id')).text or '',
                )
            )
        return entries

    @property
    def creators(self):
        return self.xpath(self.root, "dc:creator")

    @property
    def creators_with_roles(self):
        entries = []
        for elem in self.xpath(self.root, "dc:creator"):
            entries.append(
                (elem.text or '', self.element("opf:meta", refines='#%s' % elem.get('id')).text)
            )
        return entries

    @property
    def contributors(self):
        return self.xpath(self.root, "dc:contributor")

    @property
    def subjects(self):
        return self.xpath(self.root, "dc:subject")
