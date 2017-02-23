
from bl.dict import Dict
from bxml import XML
from . import NS    

class Document(XML):
    ROOT_TAG = "{%(pub)s}document" % NS
    NS = Dict(**{k:NS[k] for k in NS if k in ['html', 'pub', 'epub']})

    @classmethod
    def load(C, fn=None, section_id=None, **args):
        x = C(fn=fn, **args)
        if section_id is not None:
            from bxml.builder import Builder
            nsmap = {None:C.NS.html, 'pub':C.NS.pub, 'opf':C.NS.opf, 'dc':C.NS.dc}
            B = Builder(default=C.NS.html, nsmap=nsmap, **C.NS)
            section = C.find(x.root, "//*[@id='%s']" % section_id)
            x.root = B.pub.document('\n\t', B._.body('\n', section))
            x.fn = os.path.splitext(x.fn)[0] + '_' + section_id + '.xml'
            if section is not None and section.get('title') is not None:
                head = B._.head('\n\t\t', B._.title(section.get('title')), '\n\t'); head.tail='\nt'
                x.root.insert(0, head)
        return x

    def html(self, fn=None, ext='.xhtml', output_path=None, resources=[], **args):
        from .converters.document_html import DocumentHtml
        converter = DocumentHtml()
        nsmap = {None:C.NS.html, 'pub':C.NS.pub, 'opf':C.NS.opf, 'dc':C.NS.dc}
        B = Builder(default=C.NS.html, nsmap=nsmap, **C.NS)
        fn = fn or os.path.splitext(self.fn)[0] + ext
        output_path = output_path or self.path
        
        # pre-process: get includes
        for incl in self.root.xpath("//pub:include", namespaces=C.NS):
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
