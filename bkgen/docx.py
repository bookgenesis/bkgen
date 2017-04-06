
import os
from lxml import etree
from bl.url import URL
import bxml.docx
from bkgen import NS, Source

class DOCX(bxml.docx.DOCX, Source):
    """A Word document can be a source that is brought in, and an output format"""

    def document(self, fn=None): 
        """returns an XML document containing the content of the Word document"""
        from .converters.docx_document import DocxDocument
        converter = DocxDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml')
        return doc

    def documents(self):
        """return a list of documents containing the content of the document"""
        # just the one document
        return [self.document()]

    def images(self):
        """all the images referred to in the DOCX. 
        """
        from bf.image import Image
        images = []
        rels = self.xml(src='word/_rels/document.xml.rels').root
        for img in self.root.xpath("//html:img", namespaces=DOCX.NS):
            image = Image()
            link_rel = XML.find(rels, "//rels:Relationship[@Id='%s']" % img.get('data-link-id'), namespaces=DOCX.NS)
            embed_rel = XML.find(rels, "//rels:Relationship[@Id='%s']" % img.get('data-embed-id'), namespaces=DOCX.NS)
            if link_rel is not None:
                image.fn = URL(link_rel.get('Target')).path
                if embed_rel is not None:
                    image.data = self.read('word/' + embed_rel.get('Target'))
                    image.fn = os.path.join(self.path, img.attrib.pop('name'))
                else:
                    image.data = open(image.fn, 'rb').read()
            images.append(image)
        return images

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        from .metadata import Metadata
        xml = self.xml(src="docProps/core.xml", XMLClass=Metadata)
        xml.root.tag = "{%(pub)s}metadata" % NS
        return xml

    def stylesheet(self):
        return super().stylesheet()
