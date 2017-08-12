"""convert pub:document and document fragments to (X)HTML"""

import os, logging
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bl.string import String
from bxml.xml import XML

from bkgen import NS
from bkgen.html import HTML
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)

B = Builder(default=NS.html, **{'html':NS.html, 'pub':NS.pub})
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
    root = fill_head(root, **params)
    root = omit_print_conditions(root, **params)
    root = omit_unsupported_font_formatting(root, **params)
    root = render_footnotes(root, **params)
    root = process_endnotes(root, **params)
    return [ root ]

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

def omit_print_conditions(root, **params):
    for conditional_elem in XML.xpath(root, "//html:*[@pub:cond]", namespaces=NS):
        if 'print' in conditional_elem.get("{%(pub)s}cond" % NS).lower():
            XML.remove(conditional_elem, leave_tail=True)
    return root

def omit_unsupported_font_formatting(root, **params):
    # omit unsupported font formatting
    for span in XML.xpath(root, "//html:span", namespaces=NS):
        for key in [key for key in span.attrib.keys() if key not in ['class', 'id', 'style']]:
            _=span.attrib.pop(key)
    return root

def render_footnotes(root, **params):
    """render the footnotes within the given section at the end of the section"""
    sections = root.xpath(".//html:section", namespaces=NS)
    for section in sections:
        footnotes_section = XML.find(section, ".//html:section[@class='footnotes']", namespaces=NS)
        if footnotes_section is None:
            footnotes_section = H.section('\n', {'class':'footnotes'}); footnotes_section.tail='\n'
            section.append(footnotes_section)

        section_footnotes = XML.xpath(section, ".//pub:footnote", namespaces=NS)
        for footnote in section_footnotes:
            parent = footnote.getparent()
            fnum = footnote.get('title') or str(section_footnotes.index(footnote)+1)
            fnid = footnote.get('id') or "fn-%s" % fnum
            fnrefid = XML.find(footnote, "pub:footnote-ref/@id", namespaces=NS) or fnid.replace('fn-', 'fnref-')
            fnlink = H.a(fnum, href="#%s" % fnid, id=fnrefid)
            parent.insert(parent.index(footnote), fnlink)
            XML.remove(footnote, leave_tail=True)
            fnref = XML.find(footnote, ".//pub:footnote-ref", namespaces=NS) 
            fnreflink = H.a(fnum, href="#%s" % fnrefid, id=fnid)
            if fnref is not None:
                fnref.getparent().replace(fnref,  fnreflink)
            else:
                firstp = XML.find(footnote, "html:p", namespaces=NS)
                firstp.insert(0, fnreflink)
                firstp.text, fnreflink.tail = '', firstp.text or ''
            footnotes_section.append(footnote)
            XML.replace_with_contents(footnote)
        if len(footnotes_section.getchildren())==0:
            XML.remove(footnotes_section)
    return root

def render_endnotes(endnotes_elem, endnotes):
    """insert the collected endnotes into the given endnotes_elem"""
    endnotes_elem.tag = "{%(html)s}section" % NS
    endnotes_elem.set('class', 'endnotes')
    endnotes_elem.text = endnotes_elem.tail = '\n'
    for endnote in endnotes:
        endnotes_elem.append(endnote)
        endnote.tail='\n'
    return endnotes_elem

def process_endnotes(root, endnotes=[], insert_endnotes=False, **params):
    """collect endnotes from the content in params['endnotes'], and output them at <pub:endnotes/>.
    If insert_endnotes=True, then insert any remaining endnotes at the end of the document.
    """
    elem = XML.find(root, "//pub:endnote | //pub:endnotes", namespaces=NS)
    while elem is not None:
        if elem.tag=="{%(pub)s}endnotes" % NS:      # render the collected endnotes here
            elem = render_endnotes(elem, endnotes)
        else:                                       # render the endnote reference link here and collect the endnote
            enum = elem.get('title') or str(len(endnotes)+1)
            enid = elem.get('id') or "en-%s" % enum
            enrefid = XML.find(elem, ".//pub:endnote-ref/@id", namespaces=NS) or enid.replace('en-', 'enref-')
            enlink = H.a(enum, href="#%s" % enid, id=enrefid)
            enreflink = H.a(enum, href="#%s" % enrefid)
            endnote = H.section({'id':enid, 'class':'endnote', 'title':elem.get('title') or enum})
            for e in elem.getchildren():
                endnote.append(e)
            elem.getparent().replace(elem, enlink)
            enref = XML.find(endnote, ".//pub:endnote-ref", namespaces=NS)
            enref.getparent().replace(enref, enreflink)
            endnote = etree.fromstring(etree.tounicode(endnote).replace(' xmlns:pub="http://publishingxml.org/ns"',''))
            endnotes.append(endnote)
        elem = XML.find(root, "//pub:endnote | //pub:endnotes", namespaces=NS)
    if insert_endnotes==True and len(endnotes) > 0:
        body = XML.find(root, "html:body", namespaces=NS)
        body.append(render_endnotes(B.pub.endnotes(), endnotes))
    return root

