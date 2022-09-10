import importlib
import logging
import os

from bl.dict import Dict
from bl.file import File
from bl.url import URL
from bxml import XML

from bkgen import NS
from bkgen.source import Source

log = logging.getLogger(__name__)


class HTML(XML, Source):
    ROOT_TAG = "{%(html)s}html" % NS
    NS = Dict(**{k: NS[k] for k in NS if k in ['html', 'epub']})
    DEFAULT_NS = NS.html

    def document(self, fn=None, **params):
        """convert an xhtml file into a pub:document"""
        from .converters.html_document import HtmlDocument

        converter = HtmlDocument()
        fn = fn or os.path.splitext(self.clean_filename(self.fn))[0] + '.xml'
        doc = converter.convert(self, fn=fn, **params)
        return doc

    def documents(self, path=None, **params):
        path = path or self.path
        fn = (
            os.path.splitext(os.path.join(path, self.clean_filename(self.basename)))[0]
            + '.xml'
        )
        return [self.document(fn=fn, **params)]

    def images(self):
        return []

    def metadata(self):
        """return a Metadata object with the metadata in the document"""
        Metadata = importlib.import_module('bkgen.metadata').Metadata
        m = Metadata()
        return m

    def stylesheet(self):
        return self.css_template()

    def css_template(self, tags=None):
        CSS = importlib.import_module('bkgen.css').CSS
        Styles = importlib.import_module('bf.styles').Styles

        styles = Styles()
        if tags is None:
            tags = self.element_map(
                include_attribs=['class'], attrib_vals=True, hierarchy=False
            )
        for tag in [tag for tag in tags if NS.html in tag]:
            tagname = XML.tag_name(tag)
            styles[tagname] = {}
            for c in tags[tag].attributes.get('class') or []:
                for s in c.split(' '):
                    styles[tagname + '.' + s] = {}
        css = CSS(fn=os.path.splitext(self.fn)[0] + '.css', styles=styles)
        return css

    @classmethod
    def audit_links(cls, filenames):
        # document cache, to avoid repeatedly parsing the same document.
        documents = {}
        allowed_exts = {'.htm', '.html', '.xhtml', '.xml'}
        for filename in [os.path.abspath(filename) for filename in filenames]:
            document = documents.setdefault(filename, cls(fn=filename))
            for a in document.xpath(document.root, "//html:a[@href]"):
                url = URL(a.get('href'))
                if url.scheme in ['', 'file']:
                    if not url.path:
                        target_file = File(fn=document.fn)
                    else:
                        target_file = File(
                            fn=os.path.abspath(os.path.join(document.path, url.path))
                        )

                    if not target_file.exists:
                        log.warning(
                            '%s: link target file not found: %s'
                            % (document.fn, target_file.fn)
                        )
                    elif target_file.ext.lower() not in allowed_exts:
                        log.warning(
                            '%s: link target id in non-HTML/XML file: %s'
                            % (document.fn, target_file.fn)
                        )
                    elif url.fragment:
                        target_document = documents.setdefault(
                            target_file.fn, cls(fn=target_file.fn)
                        )
                        target_element = target_document.find(
                            target_document.root, "//*[@id='%s']" % url.fragment
                        )
                        if target_element is None:
                            log.warning(
                                '%s: link target id="%s" not found in target file: %s'
                                % (document.fn, url.fragment, target_file.fn)
                            )
