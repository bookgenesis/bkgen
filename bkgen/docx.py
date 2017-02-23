
import os
from lxml import etree
import bxml.docx
from bkgen import NS, Source

class DOCX(bxml.docx.DOCX, Source):
    """A Word document can be a source that is brought in, and an output format"""

    def documents(self, path=None):
        """return a list of documents containing the content of the document"""
        # just the one document
        fn = os.path.join(
                path or os.path.dirname(os.path.abspath(self.fn)),
                os.path.basename(os.path.splitext(self.fn)[0]+'.xml'))
        return [self.document(fn=fn)]

    def document(self, fn=None): 
        """returns an XML document containing the content of the Word document"""
        from converters.docx_document import DocxDocument
        converter = DocxDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml')
        return doc

    def resources(self, path=None):
        """return a list of files representing the resources in the document"""
        # currently an empty list
        return []

    def metadata(self):
        """return an opf:metadata element with the metadata in the document"""
        xml = self.xml(src="docProps/core.xml")
        xml.root.tag = "{%(pub)s}metadata" % NS
        return xml.root



