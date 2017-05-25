"""convert pub:document and document fragments to (X)HTML"""

import os, logging
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bxml.xml import XML

from bkgen import NS
from bkgen.html import HTML
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)

B = Builder(**NS)
H = Builder.single(NS.html)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocumentHtml(Converter):
    def convert(self, document, **params):
        document.render_includes()
        return document.transform(transformer, XMLClass=HTML, **params)

# == DEFAULT == 
# do XSLT on the element and return the results
@transformer.match("True")
def default(elem, **params):
    root = transformer_XSLT(elem).getroot()
    root = render_footnotes(root)
    root = fill_head(root, **params)
    # omit "Print" condition
    for conditional_elem in XML.xpath(root, "//html:*[@pub:cond]", namespaces=NS):
        if 'print' in conditional_elem.get("{%(pub)s}cond" % NS).lower():
            XML.remove(conditional_elem, leave_tail=True)
    # omit unsupported font formatting
    for span in XML.xpath(root, "//html:span", namespaces=NS):
        for key in [key for key in span.attrib.keys() if key not in ['class', 'id', 'style']]:
            _=span.attrib.pop(key)
    # # omit empty pp
    # for p in XML.xpath(root, "//html:p", namespaces=NS):
    #     XML.remove_if_empty(p)
    return [ root ]

def render_footnotes(root):
    """render the footnotes within the given section at the end of the section"""
    for section in root.xpath(".//html:section", namespaces=NS):
        footnotes = XML.find(section, ".//html:section[@class='footnotes']", namespaces=NS)
        if footnotes is None:
            footnotes = H.section('\n', {'class':'footnotes'}); footnotes.tail='\n'
            section.append(footnotes)
        for footnote in XML.xpath(section, ".//pub:footnote", namespaces=NS):
            log.debug("%s %r" % (footnote.tag, footnote.attrib))
            parent = footnote.getparent()
            fnid = section.get('id') + '_fn-' + footnote.get('id')
            fnrefid = fnid.replace('_fn-', '_fnref-')
            fnlink = H.a(footnote.get('id'), href="#%s" % fnid, id=fnrefid)
            parent.insert(parent.index(footnote), fnlink)
            firstp = XML.find(footnote, "./html:p", namespaces=NS)
            fnreflink = H.a(footnote.get('id'), href="#%s" % fnrefid, id=fnid)
            firstp.insert(0, fnreflink)
            XML.remove(footnote)
            footnotes.append(footnote)
            # XML.replace_with_contents(footnote)
        if len(footnotes.getchildren())==0:
            XML.remove(footnotes)
    return root

def fill_head(root, **params):
    head = XML.find(root, "//html:head", namespaces=NS)
    output_path = params.get('output_path') or os.path.dirname(params.get('fn'))
    if head is not None:
        if XML.find(head, "html:meta[@charset]", namespaces=NS) is None:
            head.append(H.meta(charset='UTF-8'))
        if params.get('http_equiv_content_type')==True \
        and XML.find(head, "html:meta[@http-equiv='Content-Type']", namespaces=NS) is None:
            head.append(H.meta({'http-equiv':'Content-Type', 'content':'text/html; charset=utf-8'}))
        for resource in params.get('resources') or []:
            srcfn = os.path.join(output_path, resource.get('href'))
            mimetype = File(fn=srcfn).mimetype()
            href = os.path.relpath(srcfn, os.path.dirname(params.get('fn')))
            if resource.get('class')=='stylesheet':
                head.append(H.link(rel='stylesheet', type=mimetype, href=href))
            elif resource.get('class')=='script':
                head.append(H.script(type=mimetype, src=href))
        title = XML.find(head, "//html:title", namespaces=NS)     # matches an existing <title>
        if title is None:
            title_elem = XML.find(root, "//*[@title]")
            if title_elem is not None:
                title = H.title(title_elem.get('title'))
        if title is not None:                                           # new or existing title in <head>
            head.insert(0, title)
    return root



