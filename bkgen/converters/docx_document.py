# XT stylesheet to transform Word docx to pub:document

import os, re, sys, logging
from lxml import etree
from copy import deepcopy
import urllib.parse

from bl.dict import Dict
from bl.string import String
from bl.url import URL
from bxml.docx import DOCX
from bxml.xml import XML
from bxml.xt import XT
from bxml.builder import Builder
from bxml.xslt import XSLT

from bkgen import NS
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)
B = Builder(**NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocxDocument(Converter):
    def convert(self, docx, fn=None, **params):
        return docx.transform(transformer, fn=fn, XMLClass=Document, **params)

@transformer.match("elem.tag=='{%(w)s}document'" % DOCX.NS)
def document(elem, **params):
    # Pre-Process
    root = deepcopy(elem)
    root = embed_notes(root, **params) 

    # Transform
    xsl_params = {
        'source':os.path.relpath(params['docx'].fn, os.path.dirname(params['fn']))
    }
    xsl_params = {k:etree.XSLT.strparam(xsl_params[k]) for k in xsl_params.keys()}
    root = transformer_XSLT(root, **xsl_params).getroot()

    # Post-Process
    root = get_document_metadata(root, **params)
    root = map_para_styles_levels(root, **params)
    root = map_span_styles(root, **params)
    root = font_attributes(root, **params)
    root = get_images(root, **params)
    root = resolve_hyperlinks(root, **params)
    root = nest_fields(root, **params)
    root = field_attributes(root, **params)
    root = toc_fields(root, **params)
    root = remove_empty_spans(root, **params)
    root = merge_contiguous_spans(root, **params)
    root = remove_empty_paras(root, **params)
    root = number_lists(root, **params)
    root = wrap_sections(root, **params)
    # root = split_level_sections(root, **params)
    # root = nest_level_sections(root, **params)
    root = sections_title_id(root, **params)
    root = paragraphs_with_newlines(root)

    return [ root ]

def get_document_metadata(root, **params):
    docx = params['docx']
    metadata = docx.metadata().root
    metadata.text = metadata.tail = '\n\t'
    for ch in metadata.getchildren():
        ch.tail='\n\t'
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
        if span.text in [None, ''] and len(span.getchildren())==0:
            XML.remove(span, leave_tail=True)
        elif span.attrib=={}:
            XML.replace_with_contents(span)
    return root

def remove_empty_paras(root, **params):
    for p in root.xpath(".//html:p", namespaces=NS):
        if p.text in [None, ''] and len(p.getchildren())==0:
            XML.remove(p, leave_tail=True)
    return root        

def number_lists(root, **params):
    """interpret OOXML paragraph numbering into ordered and unordered lists"""
    numbering = params['docx'].xml(src='word/numbering.xml')
    the_list = None
    first_numbered_p = XML.find(root, "//html:p[w:numPr]", namespaces=DOCX.NS)
    while first_numbered_p is not None:
        numPr = XML.find(first_numbered_p, "w:numPr", namespaces=DOCX.NS)
        level = XML.find(numPr, "w:ilvl/@w:val", namespaces=DOCX.NS)
        numId = XML.find(numPr, "w:numId/@w:val", namespaces=DOCX.NS)
        XML.remove(numPr)
        first_num_params = params['docx'].numbering_params(numId, level)
        # print("first_num_params: %r" % first_num_params)
        if first_num_params.get('ul')==True:
            the_list = B.html.ul('\n\t'); the_list.tail='\n'
        else:
            the_list = B.html.ol('\n\t'); the_list.tail='\n'
            if first_num_params.get('start') is not None:
                the_list.set('start', first_num_params.get('start'))
        if first_num_params.get('numFmt') is not None:
            the_list.set('class', first_num_params.get('numFmt'))
        parent = first_numbered_p.getparent()
        parent.insert(parent.index(first_numbered_p), the_list)
        numbered_p = first_numbered_p.getnext()
        li = B.html.li(first_numbered_p); li.tail='\n\t'; li.getchildren()[-1].tail = ''
        the_list.append(li)
        while numbered_p is not None and numbered_p.tag == "{%(html)s}p" % DOCX.NS \
        and XML.find(numbered_p, "w:numPr", namespaces=DOCX.NS) is not None:
            numPr = XML.find(numbered_p, "w:numPr", namespaces=DOCX.NS)
            level = XML.find(numPr, "w:ilvl/@w:val", namespaces=DOCX.NS)
            numId = XML.find(numPr, "w:numId/@w:val", namespaces=DOCX.NS)
            num_params = params['docx'].numbering_params(numId, level)
            XML.remove(numPr)
            # print("num_params: %r" % num_params)
            if num_params == first_num_params:
                next_p = numbered_p.getnext()
                li = B.html.li(numbered_p); li.tail = '\n\t'; li.getchildren()[-1].tail = ''
                the_list.append(li)
                numbered_p = next_p
            else:
                numbered_p = None
        li.tail = '\n'
        first_numbered_p = XML.find(the_list, "following::html:p[w:numPr]", namespaces=DOCX.NS)
    return root

def wrap_sections(root, **params):
    """wrap sections divided by section breaks"""
    fn = params['fn']
    body = root.find('{%(html)s}body' % NS)
    section_ids = []
    section = B.html.section('\n'); section.tail='\n'
    body.insert(0, section)
    nxt = section.getnext()
    while nxt is not None:
        if nxt.tag == "{%(pub)s}section_end" % NS:
            # put the section_end attribs in the section
            for a in nxt.attrib:
                section.set(a, nxt.get(a))

            # start a new section
            if nxt.getnext() is not None:
                section = B.html.section('\n'); section.tail='\n'
                nxt.getparent().replace(nxt, section)
            else:
                XML.remove(nxt)
        else:
            section.append(nxt)
        nxt = section.getnext()

    return root

def split_level_sections(root, **params):
    """h1...h9 paragraphs indicate the beginning of a section;
        each level creates a new section.
    """
    body = XML.find(root, "html:body", namespaces=NS)
    level_section_xpath = """.//html:*[not(ancestor::html:table) and 
        (name()='h1' or name()='h2' or name()='h3' or name()='h4' or name()='h5' 
        or name()='h6' or name()='h7' or name()='h8' or name()='h9')]"""
    for elem in body.xpath(level_section_xpath, namespaces=NS):
        parent = elem.getparent()
        # start a section, go until another element like this one or no more available
        level_tag = elem.tag
        level = int(level_tag[-1])
        title = etree.tounicode(elem, method='text', with_tail=False).strip()
        num_sections = len(elem.xpath("//html:section", namespaces=NS))
        section = etree.Element("{%(html)s}section" % NS)
        section.text = section.tail = '\n'
        parent.insert(parent.index(elem), section)
        nxt = elem.getnext()
        section.append(elem)
        while (nxt is not None 
                and not (nxt.tag == level_tag or nxt.tag[-1] == str(level)) 
                and nxt.tag != "{%(html)s}section" % NS):
            elem = nxt
            nxt = elem.getnext()
            section.append(elem)
    return root

def nest_level_sections(root, **params):
    """h1...h9 paragraphs indicate the beginning of a nested section;
        each level creates a new nested section.
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
        if parent.index(elem) > 0 and len(parent.xpath(level_section_xpath, namespaces=NS)) > 1:
            # start a section, go until another element like this one or no more available
            level_tag = elem.tag
            level = int(level_tag[-1])
            title = etree.tounicode(elem, method='text', with_tail=False).strip()
            num_sections = len(elem.xpath("//html:section", namespaces=NS))
            section = etree.Element("{%(html)s}section" % NS)
            section.text = section.tail = '\n'
            parent.insert(parent.index(elem), section)
            nxt = elem.getnext()
            section.append(elem)
            while nxt is not None and (nxt.tag != level_tag or nxt.tag[-1] != str(level)):
                elem = nxt
                nxt = elem.getnext()
                section.append(elem)
    return root

def sections_title_id(root, **params):
    """assign a section title and id, if possible to each section in the document"""
    section_ids = []
    for section in root.xpath(".//html:section", namespaces=NS):
        xp = """html:*[name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4' 
                        or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9'][1]"""
        pp = section.xpath(xp, namespaces=NS)
        if len(pp) > 0:
            c = pp[0].get('class')
            if c is not None:
                if 'title' in c.lower() or 'heading' in c.lower():
                    # turn the first paragraph into the title, but omit comments and notes
                    xslt = etree.XSLT(
                            XSLT.stylesheet(
                                XSLT.copy_all(), 
                                XSLT.template_match("html:br", XSLT.text(' ')),
                                XSLT.template_match_omission("pub:footnote"),
                                XSLT.template_match_omission("pub:endnote"),
                                XSLT.template_match_omission("pub:comment"),
                                namespaces=NS))
                    p = xslt(pp[0]).getroot()
                    title = String(etree.tounicode(p, method='text').strip()).resub('\s+', ' ')
                elif c[-len('-head'):].lower()=='-head':
                    title = String(c[:-len('-head')]).titleify()
                elif c[-len('-first'):].lower()=='-first':
                    title = String(c[:-len('-first')]).titleify()
                elif len(section_ids)==0:
                    title = String(os.path.splitext(os.path.basename(params.get('fn') or ''))[0].replace('-',' ')).titleify()
                else:
                    title = String(c.replace('-', ' ')).titleify()
                section.set('title', title)

        id = '%s_s%d' % (String(section.get('title') or '').nameify(), len(section_ids)+1)
        section.set('id', id)
        section_ids.append(id)
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
        if style.properties.outlineLvl is not None and int(style.properties.outlineLvl.val) < 9:
            level = int(style.properties.outlineLvl.val) + 1    # 1-based
        else:
            # look for outlineLvl in the ancestry
            while style.basedOn is not None and level is None:
                style = stylemap.get(style.basedOn)
                if style.properties.outlineLvl is not None \
                and int(style.properties.outlineLvl.val) < 9:
                    level = int(style.properties.outlineLvl.val) + 1
        if level is not None:
            p.tag = "{%s}h%d" % (NS.html, level)          # change tag to h1...h9

    return root

def map_span_styles(root, **params):
    stylemap = params['docx'].stylemap(cache=True)
    for sp in root.xpath(".//html:span[@class]", namespaces=NS):
        cls = DOCX.classname(stylemap.get(sp.get('class')).name)
        sp.set('class', cls)
    return root

def font_attributes(root, **params):
    """convert font attributes to styles"""
    toggle_props = ['italic', 'bold', 'allcap', 'smcap', 'strike', 'dstrike', 'hidden']
    for span in root.xpath(".//html:span", namespaces=NS):
        class_list = [c for c in span.get('class', '').split(' ') if c != '']
        # toggle properties
        for attrib in toggle_props:
            if span.get(attrib) is None: continue
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
            if val=='superscript': class_list.append('super')
            if val=='subscript': class_list.append('sub')
        if span.get('u') is not None:
            class_list.append('u%s' % span.attrib.pop('u'))
        # create the span class
        span_class = ' '.join(sorted(list(set(class_list))))
        if span_class.strip() != '':
            span.set('class', span_class)
    return root

def get_images(root, **params):
    docx = params['docx']
    output_path = params.get('output_path') or os.path.dirname(params['fn'])
    rels = docx.xml(src='word/_rels/document.xml.rels').root
    imgs = root.xpath("//html:img", namespaces=DOCX.NS)
    for img in imgs:
        link_rel = XML.find(rels, "//rels:Relationship[@Id='%s']" % img.get('data-link-id'), namespaces=DOCX.NS)
        embed_rel = XML.find(rels, "//rels:Relationship[@Id='%s']" % img.get('data-embed-id'), namespaces=DOCX.NS)
        if link_rel is not None:
            img.set('src', link_rel.get('Target'))
        if embed_rel is not None:
            fd = docx.read('word/' + embed_rel.get('Target'))
            imgfn = os.path.join(output_path, 'images', os.path.splitext(embed_rel.get('Target'))[-1])
            if not os.path.isdir(os.path.dirname(imgfn)): 
                os.makedirs(os.path.dirname(imgfn))
            with open(imgfn, 'wb') as f: 
                f.write(fd)
            img.set('src', os.path.relpath(imgfn, output_path))
        if img.get('src') is not None:
            if img.get('data-link-id') is not None: _=img.attrib.pop('data-link-id')
            if img.get('data-embed-id') is not None: _=img.attrib.pop('data-embed-id')            
        log.debug(img.attrib)
    return root

def resolve_hyperlinks(root, **params):
    docx = params['docx']
    rels = docx.xml(src='word/_rels/document.xml.rels').root
    aa = root.xpath("//html:a[@r:id or @w:anchor]", namespaces=DOCX.NS)
    for a in aa:
        href = ''
        if a.get("{%(r)s}id" % DOCX.NS) is not None:
            rId = a.attrib.pop("{%(r)s}id" % DOCX.NS)
            rel = rels.find("{%s}Relationship[@Id='%s']" % (DOCX.NS.rels, rId))
            if rel is not None:
                href += urllib.parse.unquote(rel.get('Target').replace('.docx', '.xml'))
        if '#' not in href and a.get("{%(w)s}anchor" % DOCX.NS) is not None:
            href += "#" + a.get("{%(w)s}anchor" % DOCX.NS)
        a.set('href', href)
    return root

def merge_contiguous_spans(doc, **params):
    """if spans are next to each other and have the same attributes, merge them"""
    spans = XML.xpath(doc, "//html:span", namespaces=NS)
    spans.reverse()
    for span in spans:
        next = span.getnext()
        if span.tail in [None, ''] and next is not None \
        and span.tag==next.tag and span.attrib==next.attrib:
            XML.remove(next, leave_tail=True)
            span.text = (span.text or '') + (next.text or '')
            for ch in next.getchildren(): 
                span.append(ch)
    return doc

def paragraphs_with_newlines(root):
    """paragraphs that are not in tables, comments, footnotes, or endnotes should be followed by a newline"""
    for p in root.xpath("""//html:*[
                            not(ancestor::html:table
                                or ancestor::html:li
                                or ancestor::pub:comment 
                                or ancestor::pub:footnote 
                                or ancestor::pub:endnote)
                            and (name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4'
                                or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9')]
                        """, namespaces=NS):
        p.tail = '\n'
    return root

# == FIELDS == 

def nest_fields(root, **params):
    """fields need to be converted from a series of milestones to properly nested form"""
    
    # move TOC, ..., field_end out of parent paragraph when it's the first thing
    for field in root.xpath(".//pub:field_start[starts-with(@instr,'TOC')] | .//pub:field_end", 
                            namespaces=NS):
        parent = field.getparent()
        if parent.tag=='{%(html)s}p' % NS and parent[0]==field:
            gparent = parent.getparent()
            gparent.insert(gparent.index(parent), field)
            parent.text = (parent.text or '') + (field.tail or '')
            field.tail='\n'

    # nest fields -- this assumes fields will nest
    field_starts = root.xpath("//pub:field_start[1]", namespaces=NS)
    while len(field_starts) > 0:
        field = field_starts[0]
        field.tag = "{%(pub)s}field" % NS
        field.text, field.tail = field.tail, ''
        nxt = field.getnext()
        while nxt is not None and nxt.tag != "{%(pub)s}field_end" % NS:
            e = nxt
            nxt = field.getnext()
            if nxt is not None:
                field.append(nxt)
        if nxt is None:
            pass
            # log("ERROR: unclosed field:", field.attrib)
        elif nxt.tag == "{%(pub)s}field_end" % NS:
            XML.remove(nxt, leave_tail=True)
        else:
            pass
            # log("UNDEFINED: field ending", field.attrib)
        field_starts = root.xpath("//pub:field_start[1]", namespaces=NS)
    return root

def field_attributes(root, **params):
    """convert the Word field instructions to attributes"""
    for field in root.xpath(".//pub:field[@instr]", namespaces=NS):
        tokens = [i.strip('"') for i in re.split('(?:("[^"]+")|\s+)', field.attrib.pop('instr')) if i not in [None, '']]
        cls = tokens.pop(0).upper()
        if cls in FIELD_TAGS:               # use the tag in FIELD_TAGS, if given
            field.tag = FIELD_TAGS[cls]
        else:                               # otherwise it's a <pub:field class="cls"/>
            field.set('class', cls)
        attributes, tokens = parse_field_attributes(cls, tokens)
        for k in attributes.keys():
            field.set(k, attributes[k])
        if len(tokens) > 0:
            field.set('instr', ' '.join(tokens))
    return root

def parse_field_attributes(cls, tokens):
    attr = Dict()
    if FIELD_TEMPLATES.get(cls) is not None:
        template = FIELD_TEMPLATES.get(cls)

        if template.get('') is not None:    # first token is a value
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
    """TOC fields usually have PAGEREF fields inside them, but the main text of each entry is not linked.
    Add a link to the main text of each entry that has a PAGEREF field but no link."""
    for toc in root.xpath("//pub:field[@class='TOC']", namespaces=NS):
        for p in toc.xpath(".//html:p[.//pub:field[@class='PAGEREF'] and not(.//html:a[@href])]", namespaces=NS):
            pageref = p.xpath(".//pub:field[@class='PAGEREF']", namespaces=NS)[0]
            a = B.html.a({'href': "#"+pageref.get('anchor')})
            # put content into a hyperlink, up to a pub:tab or pub:field[@class='PAGEREF']
            a.text, p.text = p.text, ''
            for ch in p.getchildren():
                while ch.tag != '{%(pub)s}tab' % NS and (
                        ch.tag != '{%(pub)s}field' % NS 
                        or ch.get('class') != 'PAGEREF'):
                    a.append(ch)
            p.insert(0, a)
    return root

FIELD_TAGS = {
    'HYPERLINK': "{%(html)s}a" % NS
}

FIELD_TEMPLATES = {
    # date and time
    'DATE': { 
        r'\@': ['msdate'],
        r'\s': ['saka', 'true']
    },
    'CREATEDATE': {
        r'\@': ['msdate'],
        r'\s': ['saka', 'true']
    },
    'PRINTDATE': {
        r'\@': ['msdate'],
        r'\s': ['saka', 'true']
    },
    'SAVEDATE': {
        r'\@': ['msdate'],
        r'\s': ['saka', 'true']
    },
    'TIME': {
        r'\@': ['msdate']
    },
    'EDITTIME': {
        r'\*': ['msformat']
    },

    # document information
    'AUTHOR': {
        r'\*': ['msformat'],
    },
    'TITLE': {
        r'\*': ['msformat']
    },
    'FILENAME': {
        r'\*': ['msformat'],
        r'\p': ['path', 'true']
    },
    'FILESIZE': {
        r'\#': ['msnumpic'],
        r'\k': ['unit', 'KB'],
        r'\m': ['unit', 'MB']
    },
    'DOCPROPERTY': {
        '': ['name']
    },
    'INFO': {
        '': ['name']
    },
    'KEYWORDS': {
        r'\*': ['msformat']
    },
    'LASTSAVEDBY': {
        r'\*': ['msformat']
    },
    'NUMCHARS': {},
    'NUMWORDS': {},
    'NUMPAGES': {},
    'SUBJECT': {
        r'\*': ['msformat']
    },
    'TEMPLATE': {
        r'\*': ['msformat'],
        r'\p': ['path', 'true']        
    },
    
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
        r'\y': ['yomi', 'true']
    },
    'RD': {     # reference document for tables/indexes
        '': ['src']
    },
    'TA': {     # table of authorities entry
        r'\b': ['bold', 'true'],
        r'\c': ['catnum'],
        r'\i': ['ital', 'true'],
        r'\the_list': ['title'],
        r'\r': ['anchor'],
        r'\s': ['name']
    },
    'TC': {     # table of contents entry
        '': ['title'],
        r'\f': ['kind'],
        r'\the_list': ['level'],
        r'\n': ['page', 'false']
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
        r'\p': ['passim', '5']   
    },
    'TOC': {
        r'\a': ['figures', ''],     # table of figures w/o labels
        r'\b': ['anchor'],        # anchor of document section to use
        r'\c': ['figures'],         # table of figures of the given label
        r'\d': ['seq-sep'],         # separator between sequence and page number
        r'\f': ['use-tc', 'true'],      # TOC from TC fields
        r'\the_list': ['tc-level'],        # TC entry field level to use
        r'\h': ['link', 'true'],
        r'\n': ['numbers', 'false'],# don't show page numbers
        r'\o': ['levels'],         # TOC from given outline levels
        r'\p': ['entry-sep'],       # separator between entry and page number
        r'\s': ['seq-type'],        # use sequence type
        r'\t': ['styles'],          # TOC from styles
        r'\w': ['preserve-tab', 'true'],
        r'\x': ['preserve-newline', 'true'],
    },
    'XE': {
        r'\b': ['bold', 'true'],
        r'\f': ['kind'],
        r'\i': ['ital', 'true'],
        r'\r': ['anchor'],
        r'\t': ['text'],
        r'\y': ['yomi']
    },
    
    # links and references
    'AUTOTEXT': {
        '': ['name']
    },
    'AUTOTEXTLIST': {
        r'\s': ['style'],
        r'\t': ['tip'],
        r'\*': ['msformat']
    },
    'HYPERLINK': {
        '': ['href'],
    },
    'INCLUDEPICTURE': {
        '': ['src'],
        r'\c': ['filter'],
        r'\d': ['embed', 'false']
    },
    'INCLUDETEXT': {
        '': ['src'],
        r'\c': ['converter'],
        r'\!': ['update', 'false'],
        r'\*': ['msformat']
    },
    'NOTEREF': {
        '': ['anchor'],
        r'\f': ['styled', 'true'],
        r'\h': None,
        r'\p': ['position', 'relative']
    },
    'PAGEREF': {
        '': ['anchor'],
        r'\h': None,                        # hyperlink flag, assumed
        r'\p': ['position', 'relative'],    # show relative position
        r'\*': ['msformat'],                # format switch
        r'\#': ['msnumpic'],                # numeric picture
    },
    'PLACEHOLDER': {
        '': ['text']
    },
    'QUOTE': {
        '': ['text']
    },
    'REF': {
        '': ['anchor'],
        r'\f': ['note-number', 'true'],
        r'\h': None,
        r'\n': ['para-number', 'copy'],
        r'\p': ['position', 'relative'],
        r'\r': ['para-number', 'relative'],
        r'\t': ['non-delimiters', 'false'],
        r'\w': ['para-number', 'absolute'],
        r'\*': ['msformat']
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
    'AUTONUM': {
        r'\s': ['sep'],
        r'\*': ['msformat']
    },
    'AUTONUMLGL': {
        r'\e': ['sep', ''],
        r'\s': ['sep'],
        r'\*': ['msformat']    
    },
    'AUTONUMOUT': {},
    'LISTNUM': {
        r'\the_list': ['level'],
        r'\s': ['start']
    },
    'PAGE': {
        r'\*': ['msformat']
    },
    'REVNUM': {
        r'\*': ['msformat']
    },
    'SECTION': {
        r'\*': ['msformat']
    },
    'SECTIONPAGES': {
        r'\*': ['msformat']
    },
    'SEQ': {
        '': ['name'],
        r'\c': ['val', 'previous'],
        r'\h': ['hidden', 'true'],
        r'\n': ['val', 'next'],
        r'\r': ['reset'],
        r'\s': ['heading'],
        r'\*': ['msformat']
    },

    # user information
    'USERADDRESS': {
        r'\*': ['msformat']
    },
    'USERINITIALS': {
        r'\*': ['msformat']
    },
    'USERNAME': {
        r'\*': ['msformat']
    },
}
