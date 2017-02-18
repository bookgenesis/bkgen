"""convert pub:document and document fragments to (X)HTML"""

import os
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bxml.xml import XML

import pubxml
from pubxml.html import HTML
from pubxml.converters import Converter
from pubxml.document import Document

B = Builder(**pubxml.NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocumentHtml(Converter):
    def convert(self, document, **params):
        return document.transform(transformer, XMLClass=HTML, **params)

# == DEFAULT == 
# do XSLT on the element and return the results
@transformer.match("True")
def default(elem, **params):
    e = get_includes(elem)
    e = transformer_XSLT(e).getroot()
    e = fill_head(e, **params)
    # omit "Print" condition
    for conditional_elem in XML.xpath(e, "//html:*[@pub:cond]", namespaces=pubxml.NS):
        if 'print' in conditional_elem.get("{%(pub)s}cond" % pubxml.NS).lower():
            XML.remove(conditional_elem, leave_tail=True)
    # omit unsupported font formatting
    for span in XML.xpath(e, "//html:span", namespaces=pubxml.NS):
        for key in [key for key in span.attrib.keys() if key not in ['class', 'id', 'style']]:
            _=span.attrib.pop(key)
    # # omit empty pp
    # for p in XML.xpath(e, "//html:p", namespaces=pubxml.NS):
    #     XML.remove_if_empty(p)
    return [ e ]

def get_includes(elem):
    for incl in elem.xpath("//pub:include", namespaces=pubxml.NS):
        srcfn = os.path.join(os.path.dirname(self.fn), incl.get('src').split('#')[0])
        if os.path.exists(srcfn):
            src = XML(fn=srcfn)
            if '#' in incl.get('src'):
                srcid = incl.get('src').split('#')[-1]
                elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
            else:
                elems = XML.xpath(src.root, "html:body/*", namespaces=bg.NS)
            div = B.html.div({'class': 'include', 'title': "src='%s'" % incl.get('src')}, *elems)
            incl.getparent().replace(incl, div)
    return elem

def fill_head(elem, **params):
    head = XML.find(elem, "//html:head", namespaces=pubxml.NS)
    output_path = params.get('output_path') or os.path.dirname(params.get('fn'))
    if head is not None:
        if XML.find(head, "html:meta[@charset]", namespaces=pubxml.NS) is None:
            head.append(H.meta(charset='UTF-8'))
        if params.get('http_equiv_content_type')==True \
        and XML.find(head, "html:meta[@http-equiv='Content-Type']", namespaces=pubxml.NS) is None:
            head.append(H.meta({'http-equiv':'Content-Type', 'content':'text/html; charset=utf-8'}))
        for resource in params.get('resources') or []:
            srcfn = os.path.join(output_path, resource.get('href'))
            mimetype = File(fn=srcfn).mimetype()
            href = os.path.relpath(srcfn, os.path.dirname(params.get('fn')))
            if resource.get('class')=='stylesheet':
                head.append(H.link(rel='stylesheet', type=mimetype, href=href))
            elif resource.get('class')=='script':
                head.append(H.script(type=mimetype, src=href))
        title = XML.find(head, "//html:title", namespaces=pubxml.NS)     # matches an existing <title>
        if title is None:
            title_elem = XML.find(elem, "//*[@title]")
            if title_elem is not None:
                title = H.title(title_elem.get('title'))
        if title is not None:                                           # new or existing title in <head>
            head.insert(0, title)
    return elem


