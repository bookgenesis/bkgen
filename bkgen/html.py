
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

    @property
    def documents(self):
        return [self.document()]

    @property
    def images(self):
        return []

    @property
    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        from .metadata import Metadata
        m = Metadata()
        return m

    @property
    def stylesheet(self):
        from .css import CSS
        css = CSS()
        css.fn = os.path.splitext(self.fn)[0]+'.css'
        return css
