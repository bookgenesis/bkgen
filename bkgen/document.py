
import logging
log = logging.getLogger(__name__)

import os
from bl.dict import Dict
from bxml import XML
from bxml.builder import Builder
from . import NS
from .source import Source    

class Document(XML, Source):
    ROOT_TAG = "{%(pub)s}document" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'pub', 'epub']})

    @property
    def documents(self):
        return [self]

    @property
    def images(self):
        from bf.image import Image
        images = [
            Image(fn=os.path.join(self.path, img.get('src')))
            for img 
            in self.xpath(self.root, "//html:img[@src]", namespaces=NS)]
        return images

    @property
    def stylesheet(self):
        from .css import CSS
        cssfn = os.path.splitext(self.fn)[0]+'.css'
        if os.path.exists(cssfn):
            return CSS(fn=cssfn)

    @classmethod
    def load(C, fn=None, section_id=None, **args):
        B = Builder(default=C.NS.html, **C.NS)
        x = C(fn=fn, **args)
        if section_id is not None:
            section = C.find(x.root, "//html:section[@id='%s']" % section_id, namespaces=C.NS)
        else:
            section = C.find(x.root, "//html:section", namespaces=C.NS)
        if section is not None:
            log.debug(section.attrib)
            title = section.get('title')
            log.debug("title = %r" % title)
            title_elem = B._('title', section.get('title') or '')
            head_elem = B._.head('\n\t\t', title_elem, '\n\t')
            body_elem = B._.body('\n', section)
            x.root = B.pub.document('\n\t', head_elem, '\n\t', body_elem, '\n')
            x.fn = os.path.splitext(x.fn)[0] + '_' + section.get('id') + '.xml'
        return x

    def icml(self, **params):
        from .converters.document_icml import DocumentIcml
        converter = DocumentIcml()
        return converter.convert(self, **params)

    def html(self, fn=None, ext='.xhtml', output_path=None, resources=[], **args):
        from .converters.document_html import DocumentHtml
        converter = DocumentHtml()
        B = Builder(default=self.NS.html, **self.NS)
        fn = fn or os.path.splitext(self.fn)[0] + ext
        output_path = output_path or self.path
        
        # pre-process: get includes
        for incl in self.root.xpath("//pub:include", namespaces=self.NS):
            srcfn = os.path.join(os.path.dirname(self.fn), incl.get('src').split('#')[0])
            if os.path.exists(srcfn):
                src = XML(fn=srcfn)
                if '#' in incl.get('src'):
                    srcid = incl.get('src').split('#')[-1]
                    elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
                else:
                    elems = XML.xpath(src.root, "html:body/*", namespaces=C.NS)
                div = B.html.div({'class': 'include', 'title': "src='%s'" % incl.get('src')}, *elems)
                incl.getparent().replace(incl, div)

        h = converter.convert(self, fn=fn, output_path=output_path, resources=resources, **args)
        return h

    def html_content(self, fn=None, output_path=None, resources=[], **args):
        h = self.html(fn=fn, output_path=output_path, resources=resources, **args)
        return "\n".join([
                etree.tounicode(e, with_tail=True)
                for e in h.find(h.root, "html:body", namespaces=C.NS).getchildren()])  

    def section_content(self, section_id):
        """return an xml string containing the content of the section"""
        section = self.find(self.root, "//html:section[@id='%s']" % section_id, namespaces=C.NS)
        if section is not None:
            return (section.text or '') + ''.join([
                etree.tounicode(e, with_tail=True)
                for e in section.getchildren()])
