
import logging
log = logging.getLogger(__name__)

import os
from lxml import etree
from bl.dict import Dict
from bxml import XML
from bxml.builder import Builder
from . import NS
from .source import Source    

class Document(XML, Source):
    ROOT_TAG = "{%(pub)s}document" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'pub', 'epub']})

    def metadata(self):
        from .metadata import Metadata
        return Metadata()

    def documents(self):
        return [self]

    def images(self):
        from bf.image import Image
        images = [
            Image(fn=os.path.join(self.path, img.get('src')))
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
        B = Builder(default=C.NS.html, **C.NS)
        x = C(fn=fn, **args)
        x.fn = fn
        if id not in [None, '']:
            section = x.find(x.root, "//*[@id='%s']/ancestor-or-self::html:section[last()]" % id, namespaces=C.NS)
        else:
            section = None
        log.debug("Load %s#%s: %r" % (os.path.basename(fn), id, section.attrib if section is not None else None))
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

    def html(self, fn=None, ext='.xhtml', output_path=None, resources=[], **args):
        from .converters.document_html import DocumentHtml
        converter = DocumentHtml()
        B = Builder(default=self.NS.html, **self.NS)
        fn = fn or os.path.splitext(self.fn)[0] + ext
        output_path = output_path or self.path
        h = converter.convert(self, fn=fn, output_path=output_path, resources=resources, **args)
        return h

    def html_content(self, fn=None, output_path=None, resources=[], **args):
        h = self.html(fn=fn, output_path=output_path, resources=resources, **args)
        return "\n".join([
            etree.tounicode(e, with_tail=True)
            for e in h.find(h.root, "html:body", namespaces=NS).getchildren()])  

    def render_includes(self):
        """put included content into the <pub:include> elements in the document."""
        for incl in self.root.xpath("//pub:include", namespaces=NS):
            # remove existing content from the include
            incl.text = '\n'
            for ch in incl.getchildren():
                incl.remove(ch)

            # fill the include with the included content from the source 
            srcfn = os.path.abspath(os.path.join(os.path.dirname(self.fn), incl.get('src').split('#')[0]))
            if os.path.exists(srcfn):
                src = Document(fn=srcfn)
                if '#' in incl.get('src'):
                    srcid = incl.get('src').split('#')[-1]
                    incl_elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
                else:
                    incl_elems = XML.xpath(src.root, "html:body/*", namespaces=NS)
                for ie in incl_elems:
                    incl.append(ie)

    def section_content(self, section_id):
        """return an xml string containing the content of the section"""
        section = self.find(self.root, "//html:section[@id='%s']" % section_id, namespaces=NS)
        log.info("%s" % section_id)
        if section is not None:
            return (section.text or '') + ''.join([
                etree.tounicode(e, with_tail=True)
                for e in section.getchildren()])
