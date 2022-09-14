# XT stylesheet to transform Word docx to pub:document

import logging
import math
import os
import re
import shutil
import urllib.parse
from copy import deepcopy

from bl.dict import Dict
from bl.int import Int
from bl.string import String
from bl.url import URL
from bxml.docx import DOCX
from bxml.xml import XML
from bxml.xslt import XSLT
from bxml.xt import XT
from lxml import etree

from bkgen import NS
from bkgen.document import Document

from ._converter import Converter

log = logging.getLogger(__name__)
B = Document.Builder()
transformer = XT()
transformer_XSLT = XSLT(fn=os.path.splitext(__file__)[0] + '.xsl')


class DocxDocument(Converter):
    def convert(self, docx, fn=None, XMLClass=Document, **params):
        return docx.transform(transformer, fn=fn, XMLClass=XMLClass, **params)


@transformer.match("elem.tag=='{%(w)s}document'" % DOCX.NS)
def document(elem, **params):
    # Pre-Process
    root = deepcopy(elem)
    root = embed_notes(root, **params)

    # Transform
    xsl_params = {
        'source': os.path.relpath(params['docx'].fn, os.path.dirname(params['fn']))
    }
    xsl_params = {k: etree.XSLT.strparam(xsl_params[k]) for k in xsl_params.keys()}
    root = transformer_XSLT(root, **xsl_params).getroot()

    # == POST-PROCESS ==
    # -- document metadata --
    root = get_document_metadata(root, **params)
    # -- styles --
    root = map_para_styles_levels(root, **params)
    root = map_span_styles(root, **params)
    root = map_table_styles(root, **params)
    root = font_attributes(root, **params)
    # -- sections --
    root = nest_level_sections(root, **params)
    root = wrap_sections(root, **params)
    root = set_section_ids(root, **params)
    root = section_note_numbering(root, **params)
    # -- images and links --
    root = get_images(root, **params)
    root = resolve_hyperlinks(root, **params)
    # -- span cleanup --
    root = merge_contiguous_spans(root, **params)
    root = handle_style_overrides(root, **params)
    root = remove_empty_spans(root, **params)
    # -- cleanup notes (footnotes, endnotes) --
    root = cleanup_notes(root, **params)
    # -- fields --
    root = field_elements(root, **params)
    root = field_attributes(root, **params)
    root = toc_fields(root, **params)
    # -- lists --
    root = number_lists(root, **params)
    # -- paragraph cleanup --
    root = anchors_in_paragraphs(root)
    root = remove_empty_paras(root, **params)
    root = paragraphs_with_newlines(root)
    root = table_column_widths(root)

    return [root]


def get_document_metadata(root, **params):
    docx = params['docx']
    metadata = docx.metadata().root
    metadata.text = metadata.tail = '\n\t'
    for ch in metadata.getchildren():
        ch.tail = '\n\t'
    root.insert(0, metadata)
    return root


def embed_notes(root, **params):
    docx = params['docx']
    footnotes = docx.footnotemap()
    for elem in root.xpath("//w:footnoteReference", namespaces=DOCX.NS):
        id = elem.get("{%(w)s}id" % DOCX.NS)
        # log.debug("footnote id=%r" % id)
        note_elem = footnotes[id].elem
        parent = elem.getparent()
        parent.replace(elem, note_elem)
    endnotes = docx.endnotemap()
    for elem in root.xpath("//w:endnoteReference", namespaces=DOCX.NS):
        id = elem.get("{%(w)s}id" % DOCX.NS)
        # log.debug("endnote id=%r" % id)
        note_elem = endnotes[id].elem
        parent = elem.getparent()
        parent.replace(elem, note_elem)
    comments = docx.commentmap()
    for elem in root.xpath("//w:commentReference", namespaces=DOCX.NS):
        id = elem.get("{%(w)s}id" % DOCX.NS)
        # log.debug("comment id=%r" % id)
        note_elem = comments[id].elem
        parent = elem.getparent()
        parent.replace(elem, note_elem)
    return root


def remove_empty_spans(root, **params):
    for span in root.xpath(".//html:span", namespaces=NS):
        if span.attrib == {}:
            XML.replace_with_contents(span)
    return root


def cleanup_notes(root, **params):
    for note in Document.xpath(root, ".//pub:footnote | .//pub:endnote"):

        # Replace footnote-reference and endnote-reference spans with content
        for span in Document.xpath(
            note,
            ".//html:span[@class='footnote-reference' or @class='endnote-reference']",
        ):
            XML.replace_with_contents(span)

        # Make sure any note reference in the footnote is followed by a tab, not a space
        for note_ref in Document.xpath(
            note, ".//pub:footnote-ref | .//pub:endnote-ref"
        ):
            parent = note_ref.getparent()
            if parent.tag != "{%(html)s}span" % NS:
                span = B.html.span({'class': XML.tag_name(note) + '-text-reference'})
                parent.replace(note_ref, span)
                span.insert(0, note_ref)
                span.tail, note_ref.tail = note_ref.tail or '', ''
            else:
                parent = span
            span.set('class', XML.tag_name(note) + '-text-reference')
            span.tail = '\t' + (span.tail or '').lstrip()

    return root


def remove_empty_paras(root, **params):
    for p in root.xpath(
        """
        .//html:*[
            not(ancestor::html:table) 
            and (name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4' 
                or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9')]
    """,
        namespaces=NS,
    ):
        if p.text in [None, ''] and len(p.getchildren()) == 0:
            XML.remove(p, leave_tail=True)
    return root


def nest_level_sections(root, **params):
    """h1...h9 paragraphs indicate the beginning of a nested section;
    each level creates a new nested section.
    the section title attribute is the heading text.
    """
    body = XML.find(root, "html:body", namespaces=NS)
    level_section_xpath = """.//html:*[not(ancestor::html:table) and 
        (name()='h1' or name()='h2' or name()='h3' or name()='h4' or name()='h5' 
        or name()='h6' or name()='h7' or name()='h8' or name()='h9')]"""
    for elem in body.xpath(level_section_xpath, namespaces=NS):
        parent = elem.getparent()
        # if this is the only element at this level in this section,
        # and it's at the beginning of the section,
        # then don't make a nested section for this element -- it's already done.
        if parent.tag != '{%(html)s}section' % NS or parent.index(elem) > 0:
            # start a section, go until another element like this one or no more available
            level_tag = elem.tag
            level = int(level_tag[-1])
            section = etree.Element("{%(html)s}section" % NS)
            section.text = section.tail = '\n'
            parent.insert(parent.index(elem), section)
            nxt = elem.getnext()
            section.append(elem)
            while (
                nxt is not None
                and nxt.tag != "{%(pub)s}section_end" % NS
                and nxt.tag != level_tag
                and nxt.tag[-1] != str(level)
            ):
                elem = nxt
                nxt = elem.getnext()
                section.append(elem)
            if nxt is not None and nxt.tag == "{%(pub)s}section_end" % NS:
                for k in nxt.attrib.keys():
                    section.set(k, nxt.get(k))
                parent.remove(nxt)
            if section.get('title') is None:
                section.set('title', make_section_title(section))
    return root


def wrap_sections(root, **params):
    """wrap sections divided by section breaks (<pub:section_end> elements)"""
    body = root.find('{%(html)s}body' % NS)
    section = Document.find(body, "pub:section_end")
    while section is not None:
        section.tag = "{%(html)s}section" % NS
        prev = section.getprevious()
        while prev is not None and prev.tag != "{%(pub)s}section_end" % NS:
            section.insert(0, prev)
            prev = section.getprevious()
        if section.get('title') is None:
            title = make_section_title(section)
            if title not in ['', None]:
                section.set('title', title)
        section = Document.find(body, "pub:section_end")
    return root


def set_section_ids(root, **params):
    for section in Document.xpath(root, "//html:section"):
        section.set('id', make_section_id(section))
    return root


# *** OBSOLETE ***
def split_level_sections(root, levels=1, **params):
    """hN paragraphs (for levels in 1..9) indicate the beginning of a section;
    each creates a new section.
    """
    level_section_xpath = ' | '.join(
        [".//html:h%d[not(ancestor::html:table)]" % i for i in range(1, levels + 1)]
    )
    for elem in XML.xpath(root, level_section_xpath, namespaces=NS):
        parent = elem.getparent()
        section_end = B.pub.section_end()
        section_end.tail = '\n'
        parent.insert(parent.index(elem), section_end)
        # give the section the attributes of the section it is in.
        next_section_end = XML.find(
            section_end, "following::pub:section_end", namespaces=NS
        )
        if next_section_end is not None:
            for key in next_section_end.attrib.keys():
                section_end.set(key, next_section_end.get(key))
    return root


def make_section_title(section):
    title = ''
    xpath = """html:*[
        (name()='p' and (contains(@class,'title') or contains(@class, 'head')))
        or name()='h1' or name()='h2' or name()='h3' or name()='h4' 
        or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9'][1]"""
    p = Document.find(section, xpath, namespaces=NS)
    if p is not None:
        # turn the first paragraph into the title, but omit comments and notes
        xslt = etree.XSLT(
            XSLT.stylesheet(
                XSLT.copy_all(),
                XSLT.template_match("html:br", XSLT.text(' ')),
                XSLT.template_match_omission("pub:footnote"),
                XSLT.template_match_omission("pub:endnote"),
                XSLT.template_match_omission("pub:comment"),
                namespaces=NS,
            )
        )
        title = String(etree.tounicode(xslt(p).getroot(), method='text').strip()).resub(
            r'\s+', ' '
        )
    return title


def make_section_id(section):
    sections = Document.xpath(section, "//html:section")
    if section in sections:
        n = sections.index(section) + 1
    else:
        n = 0
    t = String(section.get('title') or '').nameify(ascii=True).strip('_')
    id = 's%d_%s' % (n, t)
    return id


# Numbered Elements: Notes and Lists

# supported non-integer number formats used in .docx (unsupported formats default to decimal)
NUMBERS_FORMATS = dict(
    lowerLetter='abcdefghijklmnopqrstuvwxyz',
    upperLetter='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    chicago=['*', '\u2020', '\u2021', '\u00A7'],
)


def formatted_number(number, format):
    """return the number that should be displayed for the given number and format"""
    num = Int(number)
    if format == 'lowerRoman':
        fmt_num = num.roman().lower()
    elif format == 'upperRoman':
        fmt_num = num.roman().upper()
    elif format in NUMBERS_FORMATS.keys():
        i = (num - 1) % len(NUMBERS_FORMATS[format])
        n = math.ceil(num / len(NUMBERS_FORMATS[format]))
        fmt_num = NUMBERS_FORMATS[format][i] * n
    else:  # default to decimal
        fmt_num = str(num)
    return fmt_num


def section_note_numbering(root, **params):
    """assign note numbering to the sections, as indicated by the note options on each section"""
    note_options = {
        'footnote-start': '1',
        'footnote-format': 'decimal',
        'footnote-restart': 'continuous',
        'endnote-start': '1',
        'endnote-format': 'lowerLetter',
        'endnote-restart': 'continuous',
    }
    fnum = enum = 1
    for section in root.xpath("//html:section", namespaces=NS):
        for key in [
            'footnote-start',
            'footnote-format',
            'footnote-restart',
            'endnote-start',
            'endnote-format',
            'endnote-restart',
        ]:
            val = section.get('{%s}%s' % (NS.pub, key))
            if val is not None:
                note_options.update(**{key: val})
        if note_options['footnote-restart'] != 'continuous':
            fnum = int(note_options['footnote-start'])
        if note_options['endnote-restart'] != 'continuous':
            enum = int(note_options['endnote-start'])
        for footnote in section.xpath('.//pub:footnote', namespaces=NS):
            footnote.set(
                'title', formatted_number(fnum, note_options['footnote-format'])
            )
            fnum += 1
        for endnote in section.xpath('.//pub:endnote', namespaces=NS):
            endnote.set('title', formatted_number(enum, note_options['endnote-format']))
            enum += 1
        log.debug("Note options: %r" % note_options)
    return root


def number_lists(root, **params):
    """interpret OOXML paragraph numbering into ordered and unordered lists"""
    numbered_p = XML.find(root, "//html:p[w:numPr]", namespaces=DOCX.NS)
    prev_num_params = Dict()
    lists = Dict()
    while numbered_p is not None:
        # build the num_params
        numPr = XML.find(numbered_p, "w:numPr", namespaces=DOCX.NS)
        numId = XML.find(numPr, "w:numId/@w:val", namespaces=DOCX.NS)
        level = int(XML.find(numPr, "w:ilvl/@w:val", namespaces=DOCX.NS))
        num_params = params['docx'].numbering_params(numId, level)
        log.debug("num_params: %r" % num_params)
        XML.remove(numPr, leave_tail=True)

        if params.get('number_lists') is False:
            if (
                num_params.id != prev_num_params.id  # new list
                or prev_num_params.level is None
                or num_params.level > prev_num_params.level
            ):  # new nested list
                if num_params.get('ul') is True:
                    lists[level] = B.html.ul('\n' + '\t' * (level + 1))
                    lists[level].tail = '\n' + '\t' * (level)
                else:
                    lists[level] = B.html.ol('\n' + '\t' * (level + 1))
                    lists[level].tail = '\n' + '\t' * (level)
                    if num_params.get('start') is not None:
                        lists[level].set('start', num_params.get('start'))
                if num_params.get('numFmt') is not None:
                    lists[level].set('class', num_params.get('numFmt'))
                if int(level) > 0 and lists.get(level - 1) is not None:
                    lists[level - 1][-1][-1].tail = '\n' + '\t' * (level + 1)
                    lists[level - 1][-1].append(lists[level])
                else:
                    parent = numbered_p.getparent()
                    parent.insert(parent.index(numbered_p), lists[level])

            li = B.html.li(numbered_p)
            li.tail = '\n' + '\t' * (level + 1)
            li.getchildren()[-1].tail = ''
            lists[level].append(li)
            prev_num_params = num_params
            numbered_p = XML.find(
                lists[level], "following::html:p[w:numPr]", namespaces=DOCX.NS
            )
        else:
            numbered_p = XML.find(
                numbered_p, "following::html:p[w:numPr]", namespaces=DOCX.NS
            )
    return root


def map_para_styles_levels(root, **params):
    """Adjust the para class to use the Word style name.
    Also convert <p> to <h#> if there is an outline level in the style."""
    stylemap = params['docx'].stylemap(cache=True)
    for p in root.xpath(".//html:p[@class]", namespaces=NS):
        style = stylemap.get(p.get('class'))

        # class name
        cls = DOCX.classname(style.name)
        p.set('class', cls)

        # outline level
        level = None
        if (
            style.properties.outlineLvl is not None
            and int(style.properties.outlineLvl.val) < 9
        ):
            level = int(style.properties.outlineLvl.val) + 1  # 1-based
        else:
            # look for outlineLvl in the ancestry
            while style.basedOn is not None and level is None:
                style = stylemap.get(style.basedOn)
                if (
                    style.properties.outlineLvl is not None
                    and int(style.properties.outlineLvl.val) < 9
                ):
                    level = int(style.properties.outlineLvl.val) + 1
        if level is not None:
            p.tag = "{%s}h%d" % (NS.html, level)  # change tag to h1...h9

    return root


def map_span_styles(root, **params):
    stylemap = params['docx'].stylemap(cache=True)
    for sp in root.xpath(".//html:span[@class]", namespaces=NS):
        cls = stylemap.get(sp.get('class'))
        if cls is not None:
            sp.set('class', DOCX.classname(cls.name))
    return root


def map_table_styles(root, **params):
    stylemap = params['docx'].stylemap(cache=True)
    for table in root.xpath(".//html:table[@class]", namespaces=NS):
        cls = stylemap.get(table.get('class'))
        if cls is not None and cls.name is not None:
            table.set('class', cls.name)
    return root


def font_attributes(root, **params):
    """convert font attributes to classes and styles"""
    toggle_props = ['italic', 'bold', 'allcap', 'smcap', 'strike', 'dstrike', 'hidden']
    for span in root.xpath(".//html:span", namespaces=NS):
        class_list = [c for c in span.get('class', '').split(' ') if c != '']
        # toggle properties
        for attrib in toggle_props:
            if span.get(attrib) is None:
                continue
            val = span.attrib.pop(attrib)
            if val in ['on', 'true', '1', 'toggle']:
                if attrib not in class_list:
                    class_list.append(attrib)
            elif val in ['off', 'false', '0']:
                if attrib in class_list:
                    _ = class_list.pop(attrib)
        # regular properties
        if span.get('valign') is not None:
            val = span.attrib.pop('valign')
            if val == 'superscript':
                class_list.append('sup')
            if val == 'subscript':
                class_list.append('sub')
        if span.get('u') is not None:
            class_list.append('u%s' % span.attrib.pop('u'))
        # create the span class
        span_class = ' '.join(sorted(list(set(class_list))))
        if span_class.strip() != '':
            span.set('class', span_class)
        # style properties -- not converted to classes
        styles = []
        if span.get('highlight') is not None:
            styles.append('background-color:%s' % span.attrib.pop('highlight'))
        elif span.get('fill') is not None:
            styles.append('background-color:#%s' % span.attrib.pop('fill'))
        if span.get('color') is not None:
            styles.append('color:#%s' % span.attrib.pop('color'))
        if len(styles) > 0:
            span.set('style', ';'.join(styles))
    return root


def get_images(root, **params):
    docx = params['docx']
    image_subdir = params.get('image_subdir') or 'images'
    output_path = params.get('output_path') or os.path.dirname(params['fn'])
    rels = docx.xml(src='word/_rels/document.xml.rels').root
    imgs = root.xpath("//html:img", namespaces=DOCX.NS)
    for img in imgs:
        embed_rel = XML.find(
            rels,
            "//rels:Relationship[@Id='%s']" % img.get('data-embed-id'),
            namespaces=DOCX.NS,
        )
        link_rel = XML.find(
            rels,
            "//rels:Relationship[@Id='%s']" % img.get('data-link-id'),
            namespaces=DOCX.NS,
        )
        # source image
        if embed_rel is not None:
            fd = docx.read('word/' + embed_rel.get('Target'))
            imgfn = os.path.join(
                output_path,
                image_subdir,
                img.get('title') or os.path.split(embed_rel.get('Target'))[-1],
            )
            if not os.path.isdir(os.path.dirname(imgfn)):
                os.makedirs(os.path.dirname(imgfn))
            with open(imgfn, 'wb') as f:
                f.write(fd)
            img.set('src', os.path.relpath(imgfn, output_path))
        elif link_rel is not None:
            img.set('src', link_rel.get('Target'))
        if img.get('src') is not None:
            srcfn = os.path.join(
                os.path.dirname(params['docx'].fn), str(URL(img.get('src')))
            )
            outfn = os.path.join(output_path, str(URL(img.get('src'))))
            if os.path.exists(srcfn) and not os.path.exists(outfn):
                shutil.copy(srcfn, outfn)
            if img.get('data-link-id') is not None:
                _ = img.attrib.pop('data-link-id')
            if img.get('data-embed-id') is not None:
                _ = img.attrib.pop('data-embed-id')
        log.debug(img.attrib)
    return root


def resolve_hyperlinks(root, **params):
    docx = params['docx']
    rels = docx.xml(src='word/_rels/document.xml.rels').root
    aa = root.xpath("//html:a[@data-rel-id or @data-anchor]", namespaces=DOCX.NS)
    for a in aa:
        href = ''
        if a.get("data-rel-id") is not None:
            rId = a.attrib.pop("data-rel-id")
            rel = rels.find("{%s}Relationship[@Id='%s']" % (DOCX.NS.rels, rId))
            if rel is not None:
                href += urllib.parse.unquote(rel.get('Target').replace('.docx', '.xml'))
        if '#' not in href and a.get("data-anchor") is not None:
            href += "#" + a.attrib.pop("data-anchor")
        a.set('href', href)
    return root


def merge_contiguous_spans(root, **params):
    """if spans are next to each other and have the same attributes, merge them"""
    return XML.merge_contiguous(root, "//html:span", namespaces=NS)


def handle_style_overrides(root, style_overrides=True, **params):
    if style_overrides is not True:
        for elem in XML.xpath(root, "//html:*[@style]", namespaces=NS):
            elem.attrib.pop('style')
    return root


def paragraphs_with_newlines(root):
    """
    Paragraphs that are not in tables, comments, footnotes, or endnotes
    should be followed by a newline
    """
    for p in root.xpath(
        """//html:*[
            not(ancestor::html:table
                or ancestor::html:li
                or ancestor::pub:comment 
                or ancestor::pub:footnote 
                or ancestor::pub:endnote)
            and (name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4'
                or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9')]
        """,
        namespaces=NS,
    ):
        p.tail = '\n'
    return root


def table_column_widths(root):
    """convert Word column widths to points (N/20)"""
    for td in XML.xpath(root, "//html:td[@width]", namespaces=NS):
        td.set('width', "%.02fpt" % (int(td.get('width')) / 20.0,))
    return root


def anchors_in_paragraphs(root):
    """make sure anchors are inside paragraphs"""
    for a in root.xpath(
        """//html:*[(name()='a' or @class='anchor') and not(
        ancestor::html:p or ancestor::html:h1 or ancestor::html:h2 or ancestor::html:h3 
        or ancestor::html:h4 or ancestor::html:h5 or ancestor::html:h6 or ancestor::html:h7 
        or ancestor::html:h8 or ancestor::html:h9)]""",
        namespaces=NS,
    ):
        nextp = XML.find(
            a,
            """following::html:p | following::html:h1 | following::html:h2 
            | following::html:h3 | following::html:h4 | following::html:h5 | following::html:h6 
            | following::html:h7 | following::html:h8 | following::html:h9""",
            namespaces=NS,
        )
        if nextp is not None:
            XML.remove(a, leave_tail=True)
            nextp.insert(0, a)
            nextp.text, a.tail = '', nextp.text or ''
    return root


# == FIELDS ==


def field_elements(root, **params):
    """fields need to be converted from a series of milestones to properly nested form"""
    # unnest pub:field_* elements so that html:p is their direct parent
    for field_elem in root.xpath(
        ".//pub:*[ancestor::html:p and contains(name(), 'field_')]", namespaces=NS
    ):
        while field_elem.getparent().tag != '{%(html)s}p' % NS:
            XML.unnest(field_elem)

    # move TOC, ..., field_end out of parent paragraph when it's the first thing
    for field in root.xpath(
        ".//pub:field_start[starts-with(@instr,'TOC')] | .//pub:field_end",
        namespaces=NS,
    ):
        parent = field.getparent()
        if (
            XML.tag_name(parent.tag)
            in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'h9']
            and parent[0] == field
            and parent.text in [None, '']
        ):
            gparent = parent.getparent()
            gparent.insert(gparent.index(parent), field)
            parent.text = (parent.text or '') + (field.tail or '')
            field.tail = '\n'

    # compile fields -- this assumes fields will compile
    fields = root.xpath("//pub:field_start", namespaces=NS)
    for field in fields:
        field.tag = "{%(pub)s}field" % NS
        field.text, field.tail = (field.tail or ''), ''
        field.set('instr', (field.get('instr') or ''))
        nxt = field.getnext()
        while nxt is not None and nxt.tag != "{%(pub)s}field_end" % NS:
            if nxt.tag == '{%(pub)s}field_instr' % NS:
                field.set(
                    'instr', field.get('instr') + (nxt.text or '') + (nxt.tail or '')
                )
                XML.remove(nxt)
            elif nxt.tag == '{%(pub)s}field_sep' % NS:
                field.text = (field.text or '') + (nxt.tail or '')
                XML.remove(nxt)
            elif XML.find(nxt, './/pub:field_instr', namespaces=NS) is not None:
                XML.replace_with_contents(nxt)
            else:
                field.append(nxt)
            nxt = field.getnext()
        if nxt is None:
            log.error("unclosed field: %r %r", field.attrib, field.text)
        elif nxt.tag == "{%(pub)s}field_end" % NS:
            XML.remove(nxt, leave_tail=True)
        else:
            log.warn("UNDEFINED FIELD END: %r %r" % (XML.tag_name(nxt), nxt.attrib))

        if field.get('instr'):
            field.set('instr', field.get('instr').strip())

    return root


def field_attributes(root, **params):
    """convert the Word field instructions to attributes"""
    for field in root.xpath(".//pub:field[@instr]", namespaces=NS):
        tokens = [
            i.strip('"')
            for i in re.split(r'(?:("[^"]+")|\s+)', field.attrib.pop('instr'))
            if i not in [None, '']
        ]
        cls = tokens.pop(0).upper()
        if cls in FIELD_TAGS:  # use the tag in FIELD_TAGS, if given
            field.tag = FIELD_TAGS[cls]
        else:  # otherwise it's a <pub:field class="cls"/>
            field.set('class', cls)
        attributes, tokens = parse_field_attributes(cls, tokens)
        for k in attributes.keys():
            field.set(k, attributes[k])
        if len(tokens) > 0:
            field.set('instr', ' '.join(tokens))

        # -- Field Post-Processing
        # <a href="file#anchor">
        if Document.tag_name(field) == 'a' and field.get('anchor') is not None:
            field.set(
                'href', (field.get('href') or '') + '#' + field.attrib.pop('anchor')
            )

    return root


def parse_field_attributes(cls, tokens):
    attr = Dict()
    if FIELD_TEMPLATES.get(cls) is not None and len(tokens) > 0:
        template = FIELD_TEMPLATES.get(cls)
        if template.get('') is not None:  # first token is a value
            attr[template.get('')[0]] = tokens.pop(0)
        while len(tokens) > 0:
            token = tokens.pop(0)
            if template.get(token) is not None:
                key = template[token][0]
                if len(template[token]) > 1:
                    value = template[token][1]
                else:
                    value = tokens.pop(0)
                attr[key] = value.strip('"').strip()
    return attr, tokens


def toc_fields(root, **params):
    """
    TOC fields usually have PAGEREF fields inside them,
    but the main text of each entry is not linked.
    Add a link to the main text of each entry that has a PAGEREF field but no link.
    """
    for toc in root.xpath("//pub:field[@class='TOC']", namespaces=NS):
        for p in toc.xpath(
            ".//html:p[.//pub:field[@class='PAGEREF'] and not(.//html:a[@href])]",
            namespaces=NS,
        ):
            pageref = p.xpath(".//pub:field[@class='PAGEREF']", namespaces=NS)[0]
            a = B.html.a({'href': "#" + pageref.get('anchor')})
            # put content into a hyperlink, up to a pub:tab or pub:field[@class='PAGEREF']
            a.text, p.text = p.text, ''
            for ch in p.getchildren():
                if ch.tag != '{%(pub)s}tab' % NS and (
                    ch.tag != '{%(pub)s}field' % NS or ch.get('class') != 'PAGEREF'
                ):
                    a.append(ch)
                else:
                    break
            p.insert(0, a)
    return root


FIELD_TAGS = {'HYPERLINK': "{%(html)s}a" % NS}

FIELD_TEMPLATES = {
    # date and time
    'DATE': {r'\@': ['msdate'], r'\s': ['saka', 'true']},
    'CREATEDATE': {r'\@': ['msdate'], r'\s': ['saka', 'true']},
    'PRINTDATE': {r'\@': ['msdate'], r'\s': ['saka', 'true']},
    'SAVEDATE': {r'\@': ['msdate'], r'\s': ['saka', 'true']},
    'TIME': {r'\@': ['msdate']},
    'EDITTIME': {r'\*': ['msformat']},
    # document information
    'AUTHOR': {r'\*': ['msformat']},
    'TITLE': {r'\*': ['msformat']},
    'FILENAME': {r'\*': ['msformat'], r'\p': ['path', 'true']},
    'FILESIZE': {r'\#': ['msnumpic'], r'\k': ['unit', 'KB'], r'\m': ['unit', 'MB']},
    'DOCPROPERTY': {'': ['name']},
    'INFO': {'': ['name']},
    'KEYWORDS': {r'\*': ['msformat']},
    'LASTSAVEDBY': {r'\*': ['msformat']},
    'NUMCHARS': {},
    'NUMWORDS': {},
    'NUMPAGES': {},
    'SUBJECT': {r'\*': ['msformat']},
    'TEMPLATE': {r'\*': ['msformat'], r'\p': ['path', 'true']},
    # equations and formulas
    # index and tables
    'Index': {
        r'\a': ['accented', 'true'],
        r'\b': ['anchor'],
        r'\c': ['cols'],
        r'\s': ['seq'],
        r'\d': ['seq-sep'],
        r'\e': ['entry-sep'],
        r'\f': ['kind'],
        r'\g': ['range-sep'],
        r'\h': ['heading'],
        r'\the_list': ['page-sep'],
        r'\p': ['letters'],
        r'\r': ['run-in', 'true'],
        r'\y': ['yomi', 'true'],
    },
    'RD': {'': ['src']},  # reference document for tables/indexes
    'TA': {  # table of authorities entry
        r'\b': ['bold', 'true'],
        r'\c': ['catnum'],
        r'\i': ['ital', 'true'],
        r'\the_list': ['title'],
        r'\r': ['anchor'],
        r'\s': ['name'],
    },
    'TC': {  # table of contents entry
        '': ['title'],
        r'\f': ['kind'],
        r'\the_list': ['level'],
        r'\n': ['page', 'false'],
    },
    'TOA': {
        r'\b': ['anchor'],
        r'\c': ['catnum'],
        r'\s': ['seq'],
        r'\d': ['seq-sep'],
        r'\e': ['entry-sep'],
        r'\f': ['formatting', 'false'],
        r'\g': ['range-sep'],
        r'\h': ['headings', 'true'],
        r'\the_list': ['page-sep'],
        r'\p': ['passim', '5'],
    },
    'TOC': {
        r'\a': ['figures', ''],  # table of figures w/o labels
        r'\b': ['anchor'],  # anchor of document section to use
        r'\c': ['figures'],  # table of figures of the given label
        r'\d': ['seq-sep'],  # separator between sequence and page number
        r'\f': ['use-tc', 'true'],  # TOC from TC fields
        r'\the_list': ['tc-level'],  # TC entry field level to use
        r'\h': ['link', 'true'],
        r'\n': ['numbers', 'false'],  # don't show page numbers
        r'\o': ['levels'],  # TOC from given outline levels
        r'\p': ['entry-sep'],  # separator between entry and page number
        r'\s': ['seq-type'],  # use sequence type
        r'\t': ['styles'],  # TOC from styles
        r'\w': ['preserve-tab', 'true'],
        r'\x': ['preserve-newline', 'true'],
    },
    'XE': {
        '': ['text'],
        r'\b': ['bold', 'true'],
        r'\f': ['kind'],
        r'\i': ['ital', 'true'],
        r'\r': ['anchor'],
        r'\t': ['text'],
        r'\y': ['yomi'],
    },
    # links and references
    'AUTOTEXT': {'': ['name']},
    'AUTOTEXTLIST': {r'\s': ['style'], r'\t': ['tip'], r'\*': ['msformat']},
    'HYPERLINK': {'': ['href'], r'\l': ['anchor']},
    'INCLUDEPICTURE': {'': ['src'], r'\c': ['filter'], r'\d': ['embed', 'false']},
    'INCLUDETEXT': {
        '': ['src'],
        r'\c': ['converter'],
        r'\!': ['update', 'false'],
        r'\*': ['msformat'],
    },
    'NOTEREF': {
        '': ['anchor'],
        r'\f': ['styled', 'true'],
        r'\h': None,
        r'\p': ['position', 'relative'],
    },
    'PAGEREF': {
        '': ['anchor'],
        r'\h': None,  # hyperlink flag, assumed
        r'\p': ['position', 'relative'],  # show relative position
        r'\*': ['msformat'],  # format switch
        r'\#': ['msnumpic'],  # numeric picture
    },
    'PLACEHOLDER': {'': ['text']},
    'QUOTE': {'': ['text']},
    'REF': {
        '': ['anchor'],
        r'\f': ['note-number', 'true'],
        r'\h': None,
        r'\n': ['para-number', 'copy'],
        r'\p': ['position', 'relative'],
        r'\r': ['para-number', 'relative'],
        r'\t': ['non-delimiters', 'false'],
        r'\w': ['para-number', 'absolute'],
        r'\*': ['msformat'],
    },
    'STYLEREF': {
        '': ['style'],
        r'\the_list': ['start', 'bottom'],
        r'\n': ['para-number', 'copy'],
        r'\p': ['position', 'relative'],
        r'\r': ['para-number', 'relative'],
        r'\t': ['non-delimiters', 'false'],
        r'\w': ['para-number', 'absolute'],
    },
    # numbering
    'AUTONUM': {r'\s': ['sep'], r'\*': ['msformat']},
    'AUTONUMLGL': {r'\e': ['sep', ''], r'\s': ['sep'], r'\*': ['msformat']},
    'AUTONUMOUT': {},
    'LISTNUM': {r'\the_list': ['level'], r'\s': ['start']},
    'PAGE': {r'\*': ['msformat']},
    'REVNUM': {r'\*': ['msformat']},
    'SECTION': {r'\*': ['msformat']},
    'SECTIONPAGES': {r'\*': ['msformat']},
    'SEQ': {
        '': ['name'],
        r'\c': ['val', 'previous'],
        r'\h': ['hidden', 'true'],
        r'\n': ['val', 'next'],
        r'\r': ['reset'],
        r'\s': ['heading'],
        r'\*': ['msformat'],
    },
    # user information
    'USERADDRESS': {r'\*': ['msformat']},
    'USERINITIALS': {r'\*': ['msformat']},
    'USERNAME': {r'\*': ['msformat']},
}
