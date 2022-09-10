# xt stylesheet to transform Word docx to pub:document

import os

from bl.file import File
from bl.string import String
from bl.url import URL
from bxml import XML
from bxml.builder import Builder
from bxml.xt import XT
from lxml import etree

from bkgen import NS
from bkgen.document import Document

from ._converter import Converter

B = Builder(**NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))


class HtmlDocument(Converter):
    def convert(self, html, **params):
        return html.transform(transformer, XMLClass=Document, **params)


@transformer.match("elem.tag=='{%(html)s}html'" % NS)
def document(elem, **params):
    root = transformer_XSLT(elem).getroot()
    root = wrap_sections(root)
    root = sections_ids(root)
    # root = p_ids(root)
    root = hrefs_to_xml(root)
    root = normalize_img_src(root)
    root = remove_empty_spans(root)
    root = remove_event_attributes(root)
    return [root]


def wrap_sections(root, body_xpath=None):
    """each level of heading creates a new section
    body_xpath = path to elements that indicate the start of a new section
    """
    body = root.find("{%(html)s}body" % NS)
    if body_xpath is None:
        body_xpath = """
              .//html:p[(contains(@class, 'Heading')
                         or contains(@class, 'heading')
                         or contains(@class, 'Dingbat')
                         or contains(@class, 'dingbat')) 
                        and not(ancestor::html:table)]
            | .//html:h1[not(ancestor::html:table)]
            | .//html:h2[not(ancestor::html:table)]
            | .//html:h3[not(ancestor::html:table)]
            """
    following_xpath = body_xpath.replace(".//", "following::")
    for elem in body.xpath(body_xpath, namespaces=NS):
        following = elem.xpath(following_xpath, namespaces=NS)
        parent = elem.getparent()
        if parent.tag != "{%(html)s}section" % NS:
            # start a section, go until another body_xpath element or no more available
            section = etree.Element("{%(html)s}section" % NS)
            section.text = section.tail = '\n'
            parent.insert(parent.index(elem), section)
            nxt = elem.getnext()
            section.append(elem)
            while nxt is not None and nxt not in following:
                elem = nxt
                nxt = elem.getnext()
                section.append(elem)
    return root


def sections_ids(root):
    """every section needs to have a title, if possible, and a unique id in the document"""
    body = root.find("{%(html)s}body" % NS)
    sections = body.xpath(".//html:section", namespaces=NS)
    title_xpath = """
          .//html:p[contains(@class, 'Title')
                    or contains(@class, 'title')
                    or contains(@class, 'Heading')
                    or contains(@class, 'heading')] 
        | .//html:h1 | .//html:h2 | .//html:h3 
        | ./html:img[contains(@class, 'title') 
                    or contains(@class, 'Title')]"""
    for section in sections:
        if section.get('title') is None:
            title_elems = section.xpath(title_xpath, namespaces=NS)
            if len(title_elems) > 0:
                title_elem = title_elems[0]
                if title_elem.tag == "{%(html)s}img" % NS:
                    title_text = title_elem.get('title') or title_elem.get('alt')
                else:
                    title_text = String(
                        etree.tounicode(title_elems[0], method='text', with_tail=False)
                    ).titleify()
                section.set('title', title_text)
        id = "s%d" % (sections.index(section) + 1,)
        if section.get('title') is not None:
            id += '_' + String(section.get('title') or '').nameify(ascii=True)
        section.set('id', id)
    return root


def p_ids(root):
    """every p needs an id"""
    paras = root.xpath(".//html:p[not(@id)]", namespaces=NS)
    for p in paras:
        # create a unique but repeatable id: sequence number + digest
        id = "p%d_%s" % (
            paras.index(p) + 1,
            String(etree.tounicode(p, method='text', with_tail=False)).digest()[:4],
        )
        p.set('id', id)
    return root


def hrefs_to_xml(root):
    """hrefs to html files in this document space need to be to xml files instead."""
    for a in root.xpath("//*[contains(@href, 'html')]", namespaces=NS):
        url = URL(a.get('href'))
        if url.host in ['', None] and 'html' in url.path:
            url.path = os.path.splitext(url.path)[0] + '.xml'
        a.set('href', str(url))
    return root


def normalize_img_src(root):
    for e in root.xpath("//html:img[@src]", namespaces=NS):
        src = File(fn=str(URL(e.get('src'))))
        newfn = src.clean_filename()
        if newfn != src.fn:
            os.rename(src.fn, newfn)
            e.set('src', newfn)
    return root


def remove_empty_spans(root):
    """all empty spans should be removed, as they confuse web browsers"""
    for span in [
        span
        for span in root.xpath("//html:span", namespaces=NS)
        if span.text in [None, ''] and len(span.getchildren()) == 0
    ]:
        XML.remove(span, leave_tail=True)
    return root


def remove_event_attributes(root):
    """all event attributes (onLoad, etc.) should be removed."""
    for elem in root.xpath("//*[@*[starts-with(name(),'on')]]"):
        for key in [key for key in elem.attrib.keys() if key[:2] == 'on']:
            _ = elem.attrib.pop(key)
    return root
