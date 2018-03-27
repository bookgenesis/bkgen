
import logging
log = logging.getLogger(__name__)

import os, re
from lxml import etree
from bl.dict import Dict
from bl.url import URL
from bxml import XML
from bxml.builder import Builder
from . import NS
from .source import Source    

class Document(XML, Source):
    ROOT_TAG = "{%(pub)s}document" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'pub', 'epub', 'aid', 'aid5']})
    DEFAULT_NS = NS.html

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.find(self.root, "html:body", namespaces=self.NS) is None:
            H = Builder.single(self.NS.html)
            body = H.body('\n'); body.tail = '\n'
            self.root.append(body)

    @property
    def body(self):
        return self.element("html:body")

    def content_for_editing(self, elem=None):
        """return a string containing the content of the body or given element for editing
        """
        from .converters import document_html
        elem = elem or self.find(self.root, 'html:body')
        elem = document_html.render_footnotes(elem)
        elem = document_html.process_endnotes(elem, endnotes=[], insert_endnotes=True)
        elem = document_html.process_pub_attributes(elem)
        content = (elem.text or '') + ''.join([
                re.sub("<(/?pub:[^>]+)>", r"&lt;\1&gt;", etree.tounicode(e, with_tail=True))
                for e in elem.getchildren()
            ]).strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return content

    def metadata(self):
        from .metadata import Metadata
        return Metadata(root=self.find(self.root, "opf:metadata", namespaces=Metadata.NS))

    def documents(self):
        return [self]

    def images(self):
        from bf.image import Image
        images = [
            Image(fn=os.path.join(self.path, str(URL(img.get('src')))))
            for img 
            in self.xpath(self.root, "//html:img[@src]", namespaces=NS)]
        return images

    def stylesheet(self):
        from .css import CSS
        cssfn = os.path.splitext(self.fn)[0]+'.css'
        if os.path.exists(cssfn):
            return CSS(fn=cssfn)

    @classmethod
    def load(C, fn, id=None, **args):
        log.debug("fn=%r, id=%r, **%r" % (fn, id, args))
        B = C.Builder()
        x = C(fn=fn, **args)
        x.fn = fn
        if id not in [None, '']:
            section = x.find(x.root, "//*[@id='%s']" % id, namespaces=C.NS)
        else:
            section = None
        log.debug("Load %r" % section.attrib if section is not None else None)
        if section is not None:
            body_elem = B._.body('\n', section)
            x.root = B.pub.document('\n\t', body_elem, '\n')
            x.fn = os.path.splitext(x.fn)[0] + '_' + (section.get('id') or '') + '.xml'
        return x

    def icml(self, **params):
        from .converters.document_icml import DocumentIcml
        converter = DocumentIcml()
        return converter.convert(self, **params)

    def aid(self, **params):
        from .converters.document_aid import DocumentAid
        converter = DocumentAid()
        return converter.convert(self, **params)

    def html(self, fn=None, ext='.xhtml', output_path=None, resources=[], lang='en', **args):
        from .converters.document_html import DocumentHtml
        converter = DocumentHtml()
        B = self.Builder()
        fn = fn or os.path.splitext(self.fn)[0] + ext
        output_path = output_path or self.path
        h = converter.convert(self, fn=fn, output_path=output_path, resources=resources, lang=lang, **args)
        return h

    def html_content(self, fn=None, output_path=None, resources=[], **args):
        h = self.html(fn=fn, output_path=output_path, resources=resources, **args)
        return "\n".join([
            etree.tounicode(e, with_tail=True)
            for e in h.find(h.root, "html:body", namespaces=NS).getchildren()])  

    def render_includes(self, strip=False):
        """put included content into the <pub:include> elements in the document."""
        for incl in self.root.xpath("//pub:include", namespaces=NS):
            # remove existing content from the include
            incl.text = '\n'
            for ch in incl.getchildren():
                incl.remove(ch)

            # fill the include with the included content from the source 
            srcfn = os.path.abspath(os.path.join(os.path.dirname(self.fn), str(URL(incl.get('src'))).split('#')[0]))
            if os.path.exists(srcfn):
                src = Document(fn=srcfn)
                if '#' in incl.get('src'):
                    srcid = str(URL(incl.get('src'))).split('#')[-1]
                    incl_elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
                else:
                    incl_elems = XML.xpath(src.root, "html:body/*", namespaces=NS)
                for ie in incl_elems:
                    incl.append(ie)
            if strip==True: 
                self.replace_with_contents(incl)

    def section_content(self, section_id):
        """return an xml string containing the content of the section"""
        section = self.find(self.root, "//html:section[@id='%s']" % section_id, namespaces=NS)
        log.info("%s" % section_id)
        if section is not None:
            return (section.text or '') + ''.join([
                etree.tounicode(e, with_tail=True)
                for e in section.getchildren()])

    BANNED_ELEMENT_TAGS = ['html:script', 'html:form', 'html:input', 'html:textarea']
    BANNED_ATTRIBUTE_PATTERN = r'^on.*'
    def cleanup(self, root=None):
        """Clean root of disallowed elements and attributes; return a list of them"""
        root = root or self.root
        cleaned = {'elements': [], 'attributes': []}
        elem_xpath = ' | '.join(['//'+e for e in self.BANNED_ELEMENT_TAGS])
        for elem in self.xpath(root, elem_xpath):
            data = {'tag': self.tag_name(elem.tag), 'attrib': elem.attrib}
            self.remove(elem, leave_tail=True)
            cleaned['elements'].append(data)
        attr_xpath = '//@*[re:test(name(), "%s", "i")]' % self.BANNED_ATTRIBUTE_PATTERN
        for val in self.xpath(root, attr_xpath, namespaces={'re':"http://exslt.org/regular-expressions"}):
            data = {'name': val.attrname, 'value': str(val), 'tag': self.tag_name(val.getparent().tag)}
            _=val.getparent().attrib.pop(val.attrname)
            cleaned['attributes'].append(data)
        return cleaned
