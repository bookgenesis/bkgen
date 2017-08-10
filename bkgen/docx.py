
import os
from lxml import etree
from bl.dict import Dict
from bl.url import URL
from bxml import XML
import bxml.docx
from bkgen import NS
from bkgen.source import Source

class DOCX(bxml.docx.DOCX, Source):
    """A Word document can be a source that is brought in, and an output format"""

    def document(self, fn=None, **params): 
        """returns an XML document containing the content of the Word document"""
        from .converters.docx_document import DocxDocument
        converter = DocxDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml', **params)
        return doc

    # == Source Properties == 

    def documents(self, **params):
        """return a list of documents containing the content of the document"""
        # just the one document
        return [self.document(**params)]

    def images(self):
        """all the images referred to in the DOCX. 
        """
        from bf.image import Image
        images = []
        rels = self.xml(src='word/_rels/document.xml.rels').root
        for img in self.xml().root.xpath("//html:img", namespaces=DOCX.NS):
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

    def numbering_params(self, numId, level):
        """return numbering parameters for the given w:numId an w:lvl / w:ilvl"""
        numbering = self.xml(src='word/numbering.xml')
        params = Dict(level=str(level))
        num = XML.find(numbering.root, "//w:num[@w:numId='%s']" % numId, namespaces=self.NS)
        if num is not None:
            params.update(id=numId)
            abstractNumId = XML.find(num, "w:abstractNumId/@w:val", namespaces=self.NS)
            if abstractNumId is not None:
                abstractNum = XML.find(numbering.root, "//w:abstractNum[@w:abstractNumId='%s']" % abstractNumId, namespaces=self.NS)
                if abstractNum is not None:
                    lvl = XML.find(abstractNum, "w:lvl[@w:ilvl='%s']" % level, namespaces=self.NS)
                    if lvl is not None:
                        params['start'] = XML.find(lvl, "w:start/@w:val", namespaces=self.NS)
                        params['numFmt']  = XML.find(lvl, "w:numFmt/@w:val", namespaces=self.NS)
                        if params['numFmt'] == 'bullet':
                            params['ul'] = True
                        else:
                            params['ol'] = True
        return params

