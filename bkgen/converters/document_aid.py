"""convert pub:document and document fragments to (X)HTML"""

import logging

import os, re
from glob import glob
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bl.url import URL
from bf.css import CSS
from bxml.xml import XML

from bkgen import NS, config
from bkgen.converters import Converter
from bkgen.document import Document

B = Builder(**NS)
H = Builder.single(NS.html)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

log = logging.getLogger(__name__)
logging.basicConfig(**config.Logging)


class DocumentAid(Converter):
    def convert(self, document, **params):
        doc = document.transform(transformer, **params)
        return doc


# == DEFAULT ==
# do XSLT on the element and return the results
@transformer.match("True")
def default(elem, **params):
    root = get_includes(elem, **params)
    root = transformer_XSLT(root).getroot()
    root = image_hrefs(root, **params)
    root = paragraph_returns(root, **params)
    root = dt_nobreak_cstyle(root)
    root = aid_style_names(root)
    root = table_column_widths(root)
    # root = special_characters(root, **params)
    return [root]


def get_includes(root, **params):
    for incl in root.xpath(".//pub:include", namespaces=NS):
        for ch in incl:
            incl.remove(ch)
        srcfn = os.path.join(os.path.dirname(params['fn']), str(URL(incl.get('src'))).split('#')[0])
        log.debug(srcfn)
        assert os.path.exists(srcfn)
        src = XML(fn=srcfn)
        if '#' in incl.get('src'):
            srcid = str(URL(incl.get('src'))).split('#')[-1]
            elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
        else:
            elems = XML.xpath(src.root, "html:body/*", namespaces=NS)
        for elem in elems:
            if len(elem.xpath(".//pub:include", namespaces=NS)) > 0:
                elem = get_includes(elem, **params)
            incl.append(elem)
    return root


def special_characters(root, **params):
    """tag special characters with <pub:x*>...</pub:x*> so that they can be rendered correctly in 
    InDesign
    """
    for elem in root.xpath("//*[text()]"):
        elem.text = (
            (elem.text or '')
            .replace('\u00A0', '[pub:x00A0]\u00A0[/pub:x00A0]')
            .replace('\u00AD', '[pub:x00AD]\u00AD[/pub:x00AD]')
            .replace('\u2002', '[pub:x2002]\u2002[/pub:x2002]')
            .replace('\u2003', '[pub:x2003]\u2003[/pub:x2003]')
            .replace('\u2007', '[pub:x2007]\u2007[/pub:x2007]')
            .replace('\u2008', '[pub:x2008]\u2008[/pub:x2008]')
            .replace('\u2009', '[pub:x2009]\u2009[/pub:x2009]')
            .replace('\u200A', '[pub:x200A]\u200A[/pub:x200A]')
            .replace('\u2011', '[pub:x2011]\u2011[/pub:x2011]')
            .replace('\u202F', '[pub:x202F]\u202F[/pub:x202F]')
        )
        elem.tail = (
            (elem.tail or '')
            .replace('\u00A0', '[pub:x00A0]\u00A0[/pub:x00A0]')
            .replace('\u00AD', '[pub:x00AD]\u00AD[/pub:x00AD]')
            .replace('\u2002', '[pub:x2002]\u2002[/pub:x2002]')
            .replace('\u2003', '[pub:x2003]\u2003[/pub:x2003]')
            .replace('\u2007', '[pub:x2007]\u2007[/pub:x2007]')
            .replace('\u2008', '[pub:x2008]\u2008[/pub:x2008]')
            .replace('\u2009', '[pub:x2009]\u2009[/pub:x2009]')
            .replace('\u200A', '[pub:x200A]\u200A[/pub:x200A]')
            .replace('\u2011', '[pub:x2011]\u2011[/pub:x2011]')
            .replace('\u202F', '[pub:x202F]\u202F[/pub:x202F]')
        )
    root = etree.fromstring(re.sub(r"\[(/?pub:[^\]]*?)\]", r"<\1>", etree.tounicode(root)))
    return root


def image_hrefs(root, **params):
    for img in root.xpath("//html:img", namespaces=NS):
        img.set('href', 'file://' + str(URL(img.get('src'))))  # relative paths are fine in AID XML.
    return root


def paragraph_returns(root, **params):
    """Put a paragraph return at the end of every paragraph/heading that has following content.
    The paragraph return goes at the end of the last text in the paragraph, in case there is a 
    span or other element at the end of the paragraph (which would cause InDesign to ignore the 
    paragraph return if it were after that element).
    """
    t = etree.tounicode(root).strip()
    t = re.sub(r'\s*\n\s*', '', t)
    root = etree.fromstring(t)
    xpath = """//html:*[
        (name()='p' or name()='li' or name()='dd' 
            or name()='h1' or name()='h2' or name()='h3' 
            or name()='h4' or name()='h5' or name()='h6' or name()='h7')
        and ((not(ancestor::html:table)
            and not(descendant::html:li or descendant::html:p or descendant::html:h1 
                or descendant::html:h2 or descendant::html:h3 or descendant::html:h4 
                or descendant::html:h5 or descendant::html:h6 or descendant::html:h7))
            or (ancestor::html:table
                and following-sibling::html:*)
            or (html:table))
    ]"""
    pp = Document.xpath(root, xpath)
    log.debug('%d paragraphs in %r' % (len(pp), root.tag))
    for p in pp:
        p.tail = '\n'
    return root


def dt_nobreak_cstyle(root):
    """remove "nobreak" from dt cstyle"""
    for dt in Document.xpath(root, "//html:dt"):
        dt.set(
            '{%(aid)s}cstyle' % NS,
            (dt.get('{%(aid)s}cstyle' % NS) or '').replace('nobreak', '').strip(),
        )
    return root


def aid_style_names(root):
    """hyphens to spaces in AID style names"""
    for elem in Document.xpath(root, "//*[@aid:pstyle]", namespaces=NS):
        pstyle = elem.get("{%(aid)s}pstyle" % NS).replace('-', ' ')
        if pstyle[: len('heading')] == 'heading':
            pstyle = pstyle.replace('heading', 'Heading')
        elem.set("{%(aid)s}pstyle" % NS, pstyle)
    for elem in Document.xpath(root, "//*[@aid:cstyle]", namespaces=NS):
        elem.set("{%(aid)s}cstyle" % NS, elem.get("{%(aid)s}cstyle" % NS).replace('-', ' '))
    for elem in Document.xpath(root, "//*[@aid5:tablestyle]", namespaces=NS):
        elem.set(
            "{%(aid5)s}tablestyle" % NS, elem.get("{%(aid5)s}tablestyle" % NS).replace('-', ' ')
        )
    for elem in Document.xpath(root, "//*[@aid5:cellstyle]", namespaces=NS):
        elem.set("{%(aid5)s}cellstyle" % NS, elem.get("{%(aid5)s}cellstyle" % NS).replace('-', ' '))
    return root


def table_column_widths(root):
    """convert table column widths to raw pts"""
    for elem in Document.xpath(root, "//*[@aid:ccolwidth]", namespaces=NS):
        width = elem.get("{%(aid)}ccolwidth" % NS)
        points_val = CSS.to_unit(width, unit=CSS.pt) / CSS.pt
        elem.set("{%(aid)}ccolwidth" % NS, points_val)
