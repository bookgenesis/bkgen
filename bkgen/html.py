
import os
from bl.dict import Dict
from bxml import XML
from bkgen import NS
from bkgen.source import Source

class HTML(XML, Source):
    ROOT_TAG = "{%(html)s}html" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'epub']})
    DEFAULT_NS = NS.html

    def document(self, fn=None, **params):
        """convert an xhtml file into a pub:document"""
        from .converters.html_document import HtmlDocument
        from .document import Document
        converter = HtmlDocument()
        fn = fn or os.path.splitext(self.clean_filename(self.fn))[0]+'.xml'
        doc = converter.convert(self, fn=fn, **params)
        return doc

    def documents(self, path=None, **params):
        path = path or self.path
        fn = os.path.splitext(os.path.join(path, self.clean_filename(self.basename)))[0] + '.xml'
        return [self.document(fn=fn, **params)]

    def images(self):
        return []

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        from .metadata import Metadata
        m = Metadata()
        return m

    def stylesheet(self):
        return self.css_template()

    def css_template(self, tags=None):
        from .css import CSS
        from bf.styles import Styles
        styles = Styles()
        if tags is None:
            tags = self.element_map(include_attribs=['class'], attrib_vals=True, hierarchy=False)
        for tag in [tag for tag in tags if NS.html in tag]:
            tagname = XML.tag_name(tag)
            styles[tagname] = {}
            for c in (tags[tag].attributes.get('class') or []):
                for s in c.split(' '):
                    styles[tagname+'.'+s] = {}
        css = CSS(fn=os.path.splitext(self.fn)[0]+'.css', styles=styles)
        return css

