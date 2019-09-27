"""convert pub:document and document fragments to (X)HTML"""

import logging
import os
import re

from bf.css import CSS
from bl.file import File
from bl.folder import Folder
from bl.url import URL
from bxml.builder import Builder
from bxml.xml import XML
from bxml.xt import XT
from lxml import etree

from bkgen import NS, config
from ._converter import Converter
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
    root = table_columns(root, **params)

    root = transformer_XSLT(root).getroot()

    root = image_hrefs(root, **params)
    root = dt_nobreak_cstyle(root)
    root = aid_style_names(root)
    root = table_column_widths(root)
    root = paragraph_returns(root, **params)
    # root = special_characters(root, **params)
    output_images(root, **params)
    return [root]


def get_includes(root, **params):
    """place the content from <pub:include/> elements, and remap the src and href attributes therein
    """
    document = params.get('xml')
    for incl in root.xpath(".//pub:include", namespaces=NS):
        for ch in incl:
            incl.remove(ch)
        srcfn = os.path.join(document.path, str(URL(incl.get('src'))).split('#')[0])
        log.debug(srcfn)
        assert os.path.exists(srcfn), f"NOT FOUND: {srcfn}"
        src = Document(fn=srcfn)
        if '#' in incl.get('src'):
            srcid = str(URL(incl.get('src'))).split('#')[-1]
            elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
        else:
            elems = XML.xpath(src.root, "html:body/*", namespaces=NS)
        for elem in elems:
            for href_elem in Document.xpath(elem, ".//*[@href]"):
                url = URL(href_elem.get('href'))
                if url.scheme in ['', 'file']:
                    hrfn = str(src.folder / url.path)
                    url.path = os.path.relpath(hrfn, document.path)
                href_elem.set('href', str(url))
            for img in Document.xpath(elem, ".//*[not(name()='include') and @src]"):
                url = URL(img.get('src'))
                if url.scheme in ['', 'file'] and url.path[0:1] != '/':
                    hrfile = src.folder / url.path
                    url.path = os.path.relpath(hrfile.fn, document.path)
                img.set('src', str(url))
            if len(elem.xpath(".//pub:include", namespaces=NS)) > 0:
                elem = get_includes(elem, **params)
            incl.append(elem)
    return root


def table_columns(root, **params):
    """record the number of columns in each table in the table element"""
    for table in XML.xpath(root, "//html:table", namespaces=NS):
        cols = max([len(tr.getchildren()) for tr in XML.xpath(table, "html:tr", namespaces=NS)])
        table.set('data-tcols', str(cols))
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
    match_elements_to_paragraph_return = """
        (name()='p' or name()='li' or name()='dd'
        or name()='h1' or name()='h2' or name()='h3' 
        or name()='h4' or name()='h5' or name()='h6' or name()='h7') 
    """
    xpath = f"""//*[
        {match_elements_to_paragraph_return}
        and (following-sibling::*
            or not(ancestor::*[
                {match_elements_to_paragraph_return}
                or name()='td' or name()='th'
            ]))
    ]"""
    p_elems = Document.xpath(root, xpath)
    log.debug('%d paragraphs in %r' % (len(p_elems), root.tag))
    for p_elem in p_elems:
        p_elem.tail = '\n'
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
    for table in Document.xpath(root, "//html:table"):
        for elem in Document.xpath(table, ".//*[@aid:ccolwidth]", namespaces=NS):
            width = elem.get("{%(aid)s}ccolwidth" % NS)
            points_val = CSS.to_unit(width, unit=CSS.pt) / CSS.pt
            elem.set("{%(aid)s}ccolwidth" % NS, str(points_val))
    return root


def output_images(root, art_path=None, **params):
    """get any referenced images and write them to the output folder"""
    src_file = params['xml']
    out_file = File(fn=params['fn'])
    out_filebase = os.path.splitext(out_file.basename)[0]
    if '.aid' in out_filebase:
        out_filebase = os.path.splitext(out_filebase)[0]
    for img in Document.xpath(root, "//html:img[@src]"):
        src_url = URL(img.get('src'))
        if src_url.scheme in ['', 'file'] and src_url.path[0:1] != '/':
            # treat it as a relative path
            src_url.path = src_file.folder / src_url.path
        src_image = File(src_url.path)
        art_image = Folder(fn=art_path or '') / img.get('src')
        if not src_image.exists and art_image.exists:
            src_image = art_image

        out_image = out_file.folder / out_filebase / src_image.basename

        if not src_image.exists:
            if not out_image.exists:
                log.warn(f"img src doesn't exists: {src_image.fn}")
                log.debug(dict(**src_url))
        elif not out_image.exists or src_image.mtime > out_image.mtime:
            src_image.write(fn=out_image.fn)
            log.info(f"wrote image file: {out_image.fn}")

        out_relpath = out_image.relpath(out_file.path)
        if out_relpath != img.get('src'):
            img.set('src', out_relpath)
            img.set('href', f"file://{out_relpath}")
