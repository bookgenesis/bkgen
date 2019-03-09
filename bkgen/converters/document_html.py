"""convert pub:document and document fragments to (X)HTML"""

import os, logging
from copy import deepcopy
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bl.string import String
from bl.url import URL
from bxml.xml import XML

from bkgen import NS
from bkgen.html import HTML
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)

B = Builder(default=NS.html, **{'html': NS.html, 'pub': NS.pub})
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
    root = html_lang(root, **params)
    root = fill_head(root, **params)
    root = filter_conditions(root, **params)
    root = omit_unsupported_font_formatting(root, **params)
    root = render_footnotes(root, **params)
    root = process_endnotes(root, **params)
    root = process_pub_attributes(root, **params)
    root = render_crossrefs(root)
    root = process_index_entries(root, **params)
    root = replace_ligature_characters(root)
    if params.get('simple_tables') == True:
        root = render_simple_tables(root)
    root = tds_with_image_style_min_width_height(root)
    return [root]


def html_lang(root, lang='en', **params):
    """make sure the html sets lang and xml:lang"""
    if root.get('lang') is None and lang is not None:
        root.set('lang', lang)
        root.set('{%(xml)s}lang' % NS, lang)
    return root


def fill_head(root, **params):
    head = XML.find(root, "//html:head", namespaces=NS)
    output_path = params.get('output_path') or os.path.dirname(params.get('fn'))
    if head is not None:
        if XML.find(head, "html:meta[@charset]", namespaces=NS) is None:
            head.append(H.meta(charset='UTF-8'))
        if params.get('http_equiv_content_type')==True \
        and XML.find(head, "html:meta[@http-equiv='Content-Type']", namespaces=NS) is None:
            head.append(
                H.meta({
                    'http-equiv': 'Content-Type',
                    'content': 'text/html; charset=utf-8'
                }))
        for resource in params.get('resources') or []:
            srcfn = os.path.join(output_path, str(URL(resource.get('href'))))
            mimetype = File(fn=srcfn).mimetype
            href = File(srcfn).relpath(os.path.dirname(params.get('fn')))
            if resource.get('class') == 'stylesheet':
                head.append(H.link(rel='stylesheet', type=mimetype, href=href))
            elif resource.get('class') == 'script':
                head.append(H.script(type=mimetype, src=href))

        # -- <title> --
        title = XML.find(head, "//html:title", namespaces=NS)  # matches an existing <title>

        # first look for @aria-labelledby
        if title is None:
            labelledby = XML.find(root, "html:body/html:*/@aria-labelledby", namespaces=NS)
            if labelledby is not None:
                title_elem = XML.find(root, "//*[@id='%s']" % labelledby)
                if title_elem is not None:
                    title = H.title(etree.tounicode(title_elem, method='text', with_tail=False))

        # then look for @aria-label or @title
        if title is None:
            title_elem = XML.find(root, "//*[@aria-label or @title]", namespaces=NS)
            if title_elem is not None:
                title = H.title(title_elem.get('aria-label') or title_elem.get('title'))

        # if we found a title, insert it
        if title is not None:  # new or existing title in <head>
            head.insert(0, title)

    return root


def filter_conditions(root, **params):
    """include a set of conditions: 
    @pub:cond indicates element inclusion, 
    @pub:condlink indicates inclusion of the link (element ancestor-or-self with @href)
    * either those specified in params['conditions'], 
    * or default to 'digital epub mobi html'.
    """
    include = (params.get('conditions') or 'digital html epub mobi').lower().split(' ')
    # element with @pub:cond that doesn't match current context is removed
    for conditional_elem in XML.xpath(root, "//html:*[@pub:cond]", namespaces=NS):
        remove = True
        conditions = conditional_elem.attrib.pop("{%(pub)s}cond" % NS).lower().split(' ')
        for condition in conditions:
            if condition in include:
                remove = False
                break
        if remove == True:
            XML.remove(conditional_elem)
    # element with @pub:condlink that doesn't match current context has the link element removed
    # (the link element is either the element itself, or an ancestor)
    for conditional_elem in XML.xpath(
            root, "//html:*[@pub:condlink][ancestor-or-self::html:*[@href]]", namespaces=NS):
        remove = True
        conditions = conditional_elem.attrib.pop("{%(pub)s}condlink" % NS).lower().split(' ')
        for condition in conditions:
            if condition in include:
                remove = False
                break
        if remove == True:
            link_elem = XML.find(conditional_elem, "ancestor-or-self::html:*[@href]", namespaces=NS)
            XML.replace_with_contents(link_elem)
    return root


def omit_unsupported_font_formatting(root, **params):
    # omit unsupported font formatting
    supported_keys = [
        'class', 'id', 'style',
        '{%(epub)s}type' % NS, 'title', 'role', 'aria-labelledby', 'aria-label'
    ]
    for span in XML.xpath(root, "//html:span", namespaces=NS):
        for key in [key for key in span.attrib.keys() if key not in supported_keys]:
            _ = span.attrib.pop(key)
    return root


def render_footnotes(root, **params):
    """render the footnotes within the given section at the end of the section"""
    sections = root.xpath(".//html:section[@id and descendant::pub:footnote]", namespaces=NS)
    for section in sections:
        footnotes_section = XML.find(section, ".//html:section[@class='footnotes']", namespaces=NS)
        if footnotes_section is None:
            footnotes_section = H.section('\n', {
                'class': 'footnotes',
                'id': section.get('id') + '_footnotes'
            })
            footnotes_section.tail = '\n'
            section.append(footnotes_section)

        section_footnotes = XML.xpath(section, ".//pub:footnote", namespaces=NS)
        for footnote in section_footnotes:
            parent = footnote.getparent()
            fnum = footnote.get('title') or str(section_footnotes.index(footnote) + 1)
            fnid = footnote.get('id') or "fn-%s" % fnum
            fnrefid = XML.find(footnote, "pub:footnote-ref/@id", namespaces=NS) or fnid + 'ref'
            fnlink = H.a(fnum, href="#%s" % fnid, id=fnrefid)
            parent.insert(parent.index(footnote), fnlink)
            XML.remove(footnote, leave_tail=True)
            fnref = XML.find(footnote, ".//pub:footnote-ref", namespaces=NS)
            fnreflink = H.a(fnum, href="#%s" % fnrefid)
            if fnref is not None:
                fnref.getparent().replace(fnref, fnreflink)
            else:
                firstp = XML.find(footnote, "html:p", namespaces=NS)
                firstp.insert(0, fnreflink)
                firstp.text, fnreflink.tail = '', firstp.text or ''
            footnotes_section.append(footnote)
            footnote.tag = "{%(html)s}section" % NS
            footnote.set('class', 'footnote')
        if len(footnotes_section.getchildren()) == 0:
            XML.remove(footnotes_section)
    return root


def process_endnotes(root, endnotes=[], insert_endnotes=False, **params):
    """collect endnotes from the content in params['endnotes'], 
    and output them at <pub:endnotes/> or existing <section class="endnotes"/>.
    If insert_endnotes=True, then insert any remaining endnotes at the end of the document.
    """
    endnote_xpaths = ["pub:endnote", "pub:endnotes", "html:section[@class='endnotes']"]
    elem = XML.find(root, '|'.join(['//' + x for x in endnote_xpaths]), namespaces=NS)
    while elem is not None:
        if elem.tag=="{%(pub)s}endnotes" % NS\
        or (elem.tag=="{%(html)s}section" % NS and elem.get('class')=='endnotes'):
            # render the collected endnotes here
            this_elem = render_endnotes(elem, endnotes)
        else:
            # render the endnote reference link here and collect the endnote
            enum = elem.get('title') or str(len(endnotes) + 1)
            enid = elem.get('id') or "en-%s" % enum
            enrefid = XML.find(
                elem, ".//pub:endnote-ref/@id", namespaces=NS) or enid.replace('en-', 'enref-')
            enlink = H.a(enum, href="#%s" % enid, id=enrefid)
            enreflink = H.a(enum, href="#%s" % enrefid)
            endnote = H.section({
                'id': enid,
                'class': 'endnote',
                'title': elem.get('title') or enum
            })
            for e in elem.getchildren():
                endnote.append(e)
            elem.getparent().replace(elem, enlink)
            enref = XML.find(endnote, ".//pub:endnote-ref", namespaces=NS)
            enref.getparent().replace(enref, enreflink)
            endnote = etree.fromstring(
                etree.tounicode(endnote).replace(' xmlns:pub="http://publishingxml.org/ns"', ''))
            endnotes.append(endnote)
            this_elem = enlink
        elem = XML.find(
            this_elem, '|'.join(['following::' + x for x in endnote_xpaths]), namespaces=NS)
    if insert_endnotes == True and len(endnotes) > 0:
        body = XML.find(root, "html:body", namespaces=NS)
        if body is None: body = root
        body.append(render_endnotes(B.pub.endnotes(), endnotes))
    return root


def render_endnotes(endnotes_elem, endnotes):
    """insert the collected endnotes into the given endnotes_elem"""
    if endnotes_elem.tag != "{%(html)s}section" % NS:
        endnotes_elem.tag = "{%(html)s}section" % NS
        endnotes_elem.set('class', 'endnotes')
        endnotes_elem.text = endnotes_elem.tail = '\n'
    while len(endnotes) > 0:
        endnote = endnotes.pop(0)
        endnote.tail = '\n'
        endnotes_elem.append(endnote)
    return endnotes_elem


def process_pub_attributes(root, **params):
    """put all remaining pub attributes into the style attribute with the -pub- prefix."""
    for e in Document.xpath(root, "//*[@pub:*]"):
        styles = [s.strip() for s in (e.get('style') or '').split(';') if s.strip() != '']
        for aval in Document.xpath(e, "@pub:*"):
            aname = aval.attrname.replace("{%(pub)s}" % Document.NS, '-pub-')
            _ = e.attrib.pop(aval.attrname)
            style = '%s:%s' % (aname, aval)
            styles.append(style)
        e.set('style', '; '.join(styles))
    return root


def render_crossrefs(root):
    """pub:crossref uses xpath to select content"""
    for crossref in Document.xpath(root, "//pub:crossref"):
        log.debug("pub:crossref: %r" % crossref.attrib)
        src_id = crossref.get('src').split('#')[-1]
        src_elem = Document.find(root, "//*[@id='%s']" % src_id)
        if src_elem is not None:
            crossref.text = Document.find(src_elem, crossref.get('select'))
        log.debug("select: %s" % crossref.text)
        Document.replace_with_contents(crossref)
    return root


def process_index_entries(root, **params):
    """replace index entries (pub:xe) with spans"""
    for e in Document.xpath(root, "//pub:xe"):
        e.tag = "{%(html)s}span" % Document.NS
        for key in [k for k in e.attrib.keys() if k != 'id']:
            _ = e.attrib.pop(key)
        e.set('class', 'xe')
    return root


def replace_ligature_characters(root):
    """Sometimes ligature characters (fl, fi) are used in books directly, 
    but these don't work well in HTML contexts, so replace them with their multi-character equivalents.
    """
    ligatures = {
        '\uA732': 'AA',
        '\uA733': 'aa',
        '\u00C6': 'AE',
        '\u00E6': 'ae',
        '\uA734': 'AO',
        '\uA735': 'ao',
        '\uA736': 'AU',
        '\uA737': 'au',
        '\uA738': 'AV',
        '\uA739': 'av',
        '\uA73C': 'AY',
        '\uA73D': 'ay',
        '\uFB00': 'ff',
        '\uFB03': 'ffi',
        '\uFB04': 'ffl',
        '\uFB01': 'fi',
        '\uFB02': 'fl',
        '\u0152': 'OE',
        '\u0153': 'oe',
        '\uA74E': 'OO',
        '\uA74F': 'oo',
        '\u00DF': 'fs',
        '\uFB06': 'st',
        '\uA728': 'TZ',
        '\uA729': 'tz',
        '\u1D6B': 'ue',
        '\uA760': 'VY',
        '\uA761': 'vy'
    }
    text = etree.tounicode(root)
    for lig, chars in ligatures.items():
        text = text.replace(lig, chars)
    root = etree.fromstring(text)
    return root


def render_simple_tables(root):
    """If a table's first row is <th> cells, and every row has the same number of cells,
    then convert the table into a series of two column tables, one per row, 
    with the <th> cells on the left and the <td> cells on the right.
    """
    for table in Document.xpath(root, "//html:table"):
        first_row = Document.find(table, "html:tr")
        if first_row is None: continue
        if len(first_row.getchildren()) != len(Document.xpath(first_row, "html:th")):
            continue
        additional_rows = Document.xpath(table, "html:tr")[1:]
        next_table = False
        for row in additional_rows:
            if len(row.getchildren()) != len(first_row.getchildren()):
                next_table = True
                break
        if next_table == True:
            continue
        # Okay, this is a table we can transform
        parent = table.getparent()
        for row in additional_rows:
            row_table = B.html.table('\n\t')
            row_table.tail = '\n'
            for i in range(len(first_row)):
                tr = B.html.tr('\n\t\t', deepcopy(first_row[i]), '\n\t\t', deepcopy(row[i]))
                tr.tail = '\n\t'
                row_table.append(tr)
            parent.insert(parent.index(table), row_table)
        parent.remove(table)
    return root


def tds_with_image_style_min_width_height(root):
    """`<td>`s that contain `<img>`s with style width/height set that style min-width/height."""
    for td in Document.xpath(
            root,
            "//html:td[descendant::html:img[contains(@style,'width') or contains(@style,'height')]]"
    ):
        td_style = {
            key.strip(): val.strip()
            for key, val in
            [attr.split(':') for attr in (td.get('style') or ':').strip(';').split(';')]
            if key != ''
        }
        for img in Document.xpath(
                td, "descendant::html:img[contains(@style,'width') or contains(@style,'height')]"):
            img_style = {
                key.strip(): val.strip()
                for key, val in
                [attr.split(':') for attr in (img.get('style') or ':').strip(';').split(';')]
                if key != ''
            }
            for key in ['width', 'height']:
                if key in img_style and 'min-' + key not in td_style:
                    td_style['min-' + key] = img_style[key]
            for key in ['min-width', 'min-height']:
                if key in img_style and key not in td_style:
                    td_style[key] = img_style[key]
        if len(td_style) > 0:
            td.set('style', '; '.join(["%s: %s" % (k, v) for k, v in td_style.items()]) + ';')

    return root