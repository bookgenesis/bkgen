
import os
from bxml import XML
from bkgen import NS
from bkgen.source import Source

class HTML(XML, Source):
    ROOT_TAG = "{%(html)s}html" % NS

    def document(self, fn=None, **params):
        """convert an xhtml file into a pub:document"""
        from .converters.html_document import HtmlDocument
        from .document import Document
        converter = HtmlDocument()
        doc = converter.convert(self, fn=fn or os.path.splitext(self.fn)[0]+'.xml', **params)
        return doc

    def documents(self, **params):
        return [self.document(**params)]

    def images(self):
        return []

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        from .metadata import Metadata
        m = Metadata()
        return m

    def stylesheet(self):
        return self.css_template()

    def css_template(self):
        from .css import CSS
        from bf.styles import Styles
        styles = Styles()
        tags = self.tag_dict(include_attribs=['class'])
        for tag in [tag for tag in tags if NS.html in tag]:
            tagname = XML.tag_name(tag)
            styles[tagname] = {}
            for c in (tags[tag].get('class') or []):
                styles[tagname+'.'+c] = {}
        css = CSS(fn=os.path.splitext(self.fn)[0]+'.css', styles=styles)
        return css
