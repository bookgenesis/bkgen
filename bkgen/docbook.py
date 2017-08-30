
import os
from bxml import XML
from bkgen.source import Source

class DocBook(XML, Source):
    """A Word document can be a source that is brought in, and an output format"""

    def document(self, fn=None, **params): 
        """returns an XML document containing the content of the DocBook document"""
        from .converters.docbook_document import DocBookDocument
        converter = DocBookDocument()
        fn = fn or os.path.splitext(self.clean_filename(self.fn))[0]+'.xml'
        doc = converter.convert(self, fn=fn, **params)
        return doc

    # == Source Properties == 

    def documents(self, path=None, **params):
        """return a list of documents containing the content of the document"""
        path = path or self.path
        fn = os.path.splitext(os.path.join(path, self.clean_filename(self.basename)))[0] + '.xml'
        # just the one document
        return [self.document(fn=fn, **params)]

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
