
import os
from bxml import XML
from bkgen.source import Source

class DocBook(XML, Source):
    """A Word document can be a source that is brought in, and an output format"""

    def document(self, fn=None, **params): 
        """returns an XML document containing the content of the Word document"""
        from .converters.docbook_document import DocBookDocument
        converter = DocBookDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml', **params)
        return doc

    # == Source Properties == 

    def documents(self, **params):
        """return a list of documents containing the content of the document"""
        # just the one document
        return [self.document(**params)]

    def images(self):
        """all the images referred to in the DocBook file. 
        """
        return []

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        return

    def stylesheet(self):
        """the stylesheet for the DocBook file"""
        return
