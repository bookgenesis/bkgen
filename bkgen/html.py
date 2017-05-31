
from bxml import XML
from bkgen import NS

class HTML(XML):
    ROOT_TAG = "{%(html)s}html" % NS

    def document(self, fn=None):
        """convert an xhtml file into a pub:document"""
        from .converters.html_document import HtmlDocument
        from .document import Document
        converter = HtmlDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml')
        return doc

    def documents(self):
        return [self.document()]

    def images(self):
        return []

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        from .metadata import Metadata
        m = Metadata()
        return m

    def stylesheet(self):
        from .css import CSS
        css = CSS()
        css.fn = os.path.splitext(self.fn)[0]+'.css'
        return css
