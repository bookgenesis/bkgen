# XT .icml to pub:document 

import logging
log = logging.getLogger(__name__)

import os, re, json, sys
from lxml import etree
import pycountry
from bl.id import random_id
from bl.dict import Dict
from bl.string import String
from bl.url import URL
from bl.text import Text
from bxml.xml import XML
from bxml.xt import XT
from bxml.builder import Builder
from bkgen.icml import ICML
from bkgen.converters import Converter
from bkgen.document import Document
NS = Document.NS

B = Builder(default=NS.html, **NS)
transformer = XT()

class IcmlDocument(Converter):
    def convert(self, icml, **params):
        return icml.transform(transformer, XMLClass=Document, **params)

# == Document ==
@transformer.match("elem.tag in ['Document', '{%(idPkg)s}Story']" % ICML.NS)
def Document(elem, **params):
    if params.get('document_path') is None:
        params['document_path'] = os.path.dirname(params.get('fn'))
    if params.get('fns') is not None:
        # load all the documents in params['fns']
        params['documents'] = [
            XML(fn=fn)
            for fn in params['fns']
        ]
    params['footnotes'] = []

    elem = pre_process(elem, **params)
    doc = B.pub.document('\n\t', transformer(elem.getchildren(), **params))
    doc = post_process(doc, **params)
    return [doc]

# == Story ==
@transformer.match("elem.tag=='Story'")
def Story(elem, **params):
    section = B.html.section('\n',
                transformer(elem.getchildren(), **params),
                '\n',
                id=elem.get('Self'))
    body = B.html.body('\n', section)
    body.tail = '\n'
    body = process_para_breaks(body)
    body = nest_span_hyperlinks(body)
    body = split_sections(body)
    return [body]

# == ParagraphStyleRange ==
@transformer.match("elem.tag=='ParagraphStyleRange'")
def ParagraphStyleRange(elem, **params):
    # create the p class attribute
    ps = elem.get('AppliedParagraphStyle')\
            .replace('ParagraphStyle/', '').replace('%3a', ':').replace(": ", ":")
    p_class = ICML.classname(ps)
    if 'p_class' not in params: params['p_class'] = p_class
    p = B.html.p({'class': p_class}, 
        '', transformer(elem.getchildren(), **params))
    result = [p, '\n']
    # if there is a section_start in the paragraph, move it out.
    section_start = XML.find(p, ".//pub:section_start", namespaces=NS) 
    if section_start is not None:
        XML.remove(section_start, leave_tail=True)
        result = [section_start, '\n'] + result
    return result

# == CharacterStyleRange ==
@transformer.match("elem.tag=='CharacterStyleRange'")
def CharacterStyleRange(elem, **params):
    if elem.find("Table") is not None:
        return transformer(elem.getchildren(), **params)
    else:
        cs = elem.get('AppliedCharacterStyle')\
                .replace('CharacterStyle/', '')\
                .replace('%3a', ':').replace(": ", ":")
        span_class = ICML.classname(cs)
        if 'span_class' not in params: params['span_class'] = span_class
        span = B.html.span(character_attribs(elem),
            transformer(elem.getchildren(), **params))
        if span_class not in ['', None, 'Default-Paragraph-Font', 'No-character-style']: 
            span.set('class', span_class)
        if elem.get('AppliedConditions') is not None:
            conditions = [c.replace('Condition/','').replace('%20','_') for c in elem.get('AppliedConditions').split(' ')]
            span.set('{%(pub)s}cond' % NS, ' '.join(conditions))
        span.text = ''
        span.tail = ''
        return [span]

def character_attribs(elem):
    """return common character attributes on elem"""
    attrib = Dict()
    style = Dict()
    for key in elem.attrib:
        if elem.get(key) is None:
            pass
        elif key=='Capitalization':
            val = elem.get(key)
            if val in ['SmallCaps', 'CapToSmallCap']:
                style['font-variant'] = 'small-caps'
            elif val == 'AllCaps':
                style['text-transform'] = 'uppercase'
            elif val == 'Normal':
                style['text-transform'] = 'none'
                style['font-variant'] = 'normal'
            else:
                log.warn('%s=%r' % (key, elem.get(key)))
        elif key=='FontStyle':
            for val in elem.get(key).split():
                if val == 'Italic':
                    style['font-style'] = 'italic'
                elif val == 'Bold':
                    style['font-weight'] = 'bold'
                elif val == 'Semibold':
                    style['font-weight'] = '600'
                elif val == 'Condensed':
                    style['font-stretch'] = 'condensed'
                elif val == 'Regular':
                    style['font-style'] = 'normal'
                    style['font-weight'] = 'normal'
                else:
                    log.warn('%s=%r' % (key, elem.get(key)))
        elif key=='PointSize':
            style['font-size'] = elem.get(key)+'pt'
        elif key=='Position':
            if elem.get(key)=='Superscript':
                style['vertical-align'] = 'super'
            elif elem.get(key)=='Subscript':
                style['vertical-align'] = 'sub'
            elif elem.get(key)=='Normal':
                style['vertical-align'] = 'baseline'
            else:
                log.warn('%s=%r' % (key, elem.get(key)))
        elif key == 'CharacterDirection':
            if elem.get(key)=='LeftToRightDirection':
                style['direction'] = 'ltr'
            elif elem.get(key)=='RightToLeftDirection':
                style['direction'] = 'rtl'
            elif elem.get(key) != 'DefaultDirection':
                log.warn('%s=%r' % (key, elem.get(key)))
        elif key == 'AppliedLanguage':
            try:
                # look up the language using the lovely pycountry.languages database
                lang = pycountry.languages.lookup(elem.get(key).split('/')[-1].split(':')[0])
                if lang is not None:
                    attrib.lang = lang.alpha_2
                else:
                    log.warn('%s=%r' % (key, elem.get(key)))
            except:
                log.warn(sys.exc_info()[1])
                log.warn('%s=%r' % (key, elem.get(key)))
        elif key == 'FillColor':
                style['color'] = '%s' % elem.get(key).split('/')[-1]
        elif key in ['AppliedCharacterStyle', 'AppliedConditions', 'BaselineShift', 
                'FillColor', 'FillTint', 
                'HorizontalScale', 'Kashidas', 'KerningMethod', 'KerningValue', 
                'ParagraphBreakType', 'StrokeColor', 'Tracking', 'VerticalScale']:
            pass
        else:
            log.warn('%s=%r' % (key, elem.get(key)))
    if style.keys() != []:
        attrib.style = '; '.join(["%s:%s" % (k, style[k]) for k in style.keys()])
    return attrib

@transformer.match("elem.tag=='HiddenText'")
def HiddenText(elem, **params):
    return transformer(elem.getchildren(), **{k:params[k] for k in params if '_style' not in k})

# == Note ==
@transformer.match("elem.tag=='Note'")
def Note(elem, **params):
    content = ''.join(XML.xpath(elem, ".//Content/text()") )
    if content[0:1]=='<' and content[-1:]=='>':
        e = etree.fromstring(content)
        if e.tag=="img" and e.get('src') is not None: # make sure \w => - in img src
            l = e.get('src').split('/')
            l[-1] = re.sub("(&[\w^;]+;|[\s\&+;'])", "-", l[-1])
            e.set('src', '/'.join(l))
        return [e]
    else:
        return []
    # return transformer(tagged_content, **params)

# == Content ==
@transformer.match("elem.tag=='Content'")
def Content(elem, **params):
    # create a temporary container -- will be stripped later. 
    t = B.pub.t(elem.text or '', 
                transformer(elem.getchildren(), **params))
    # \t characters to <pub:tab/>
    content = etree.fromstring(etree.tounicode(t, with_tail=False)
                .replace('\t',"<pub:tab xmlns:pub='%(pub)s'/>" % NS).encode('utf-8'))
    content.tail = ''
    return [content]

@transformer.match("elem.tag=='Br'")
def Br(elem, **params):
    # InDesign <Br/>==<pub:p_break/> indicates a paragraph break. Could be
    # within a CharacterStyleRange, or not. Could be in the
    # middle or at the end of a ParagraphStyleRange.
    return [B.pub.p_break()]

# == Footnote ==
@transformer.match("elem.tag=='Footnote'")
def Footnote(elem, **params):
    fn_params = {
        k:params[k]
        for k in params.keys()
        if k not in ['p_class', 'span_class']}
    if elem not in params['footnotes']:
        params['footnotes'].append(elem)
    fn_id = str(params['footnotes'].index(elem)+1)
    return [
        B.pub.footnote(
            # id is the index + 1 of this footnote in document footnotes
            {'id': fn_id},
            transformer(elem.getchildren(), **fn_params))
    ]

# == Table ==
@transformer.match("elem.tag=='Table'")
def Table(elem, **params):
    table = B.html.table('\n\t',
        transformer(elem.getchildren(), **params))
    return [table, '\n']

@transformer.match("elem.tag=='Row'")
def Row(elem, **params):
    tr = B.html.tr('\n\t\t')
    tail = ":" + elem.get('Name')
    for cell in [cell for cell in 
            elem.xpath("../Cell[contains(@Name, ':%s')]" % elem.get('Name'))
            if cell.get('Name')[-len(tail):] == tail]:
        tr.append(Cell(cell, **params)[0])
    return [tr, '\n\t']

def Cell(elem, **params):
    cell_params = {k:params[k] for k in params.keys()
        if k not in ['p_class', 'span_class']}
    td = B.html.td('\n',
        transformer(elem.getchildren(), **cell_params))
    col_span = elem.get('ColumnSpan')
    if int(col_span) > 1:
        td.set('colspan', col_span)
    return [td, '\n\t\t']

def make_anchor_name(name):
    """make sure the anchor name will be valid. Use this for all anchor names."""
    return String(name).identifier()

# == HyperlinkTextDestination ==
@transformer.match("elem.tag=='HyperlinkTextDestination'")
def HyperlinkTextDestination(elem, **params):
    hyperlink = ''
    result = []
    if elem.get('Name')[-4:] == '_end':
        anchor = B.pub.anchor_end(name=make_anchor_name(elem.get('Name')[:-4]))
    else:
        anchor = B.pub.anchor_start(name=make_anchor_name(elem.get('Name')))
        # If the anchor_start defines a bookmark, create a section_start as well
        # print(elem.get('Name'), elem.attrib)
        bookmark = XML.find(elem, "//Bookmark[@Destination='HyperlinkTextDestination/%s']" % elem.get('Name'))
        if bookmark is not None:
            section_start = B.pub.section_start(
                id="section_"+anchor.get('name'), 
                title=bookmark.get('Name').replace('_', ' ').strip())
            result += [section_start]
        # try to find a cross-reference source; if so, use the number and link back.
        hyperlink = XML.find(elem, "//Hyperlink[@DestinationUniqueKey='%s']" % elem.get('DestinationUniqueKey'))
        if hyperlink is not None:
            source = XML.find(elem, "//CrossReferenceSource[@Self='%s']" % hyperlink.get('Source'))
            if source is not None:
                content = source.find('Content')
                if content is not None:
                    hyperlink_anchor = make_anchor_name(source.get('Name'))
                    hyperlink_elem = B.pub.hyperlink(content.text, anchor=hyperlink_anchor)
                    return [anchor, hyperlink_elem, ' ']
    result += [anchor]
    return result

@transformer.match("elem.tag=='ParagraphDestination'")
def ParagraphDestination(elem, **params):
    anchor_name = make_anchor_name(elem.get('Name'))
    anchor_start = B.pub.anchor_start(name=anchor_name)
    # try to find the source of the paragraph cross-reference; if so, use the number and link back.
    hyperlink = ''
    hyperlinks = elem.xpath("//Hyperlink[@DestinationUniqueKey='%s']" % elem.get('DestinationUniqueKey'))
    if len(hyperlinks) > 0: 
        sources = elem.xpath("//*[@Self='%s']" % hyperlinks[0].get('Source'))
        if len(sources) > 0:
            content = sources[0].find('Content')
            if content is not None:
                hyperlink_anchor = make_anchor_name(sources[0].get('Name'))
                hyperlink = B.pub.hyperlink(content.text, anchor=hyperlink_anchor)
                return [anchor_start, hyperlink, ' ']
    return [anchor_start]


# == Hyperlink ==
def hyperlink_attribs(elem, source=None, **params):
    attribs = Dict()
    h = XML.find(elem, "//Hyperlink[@Source='%s']" % source or elem.get('Self') or '')
    if h is not None:
        destkey = h.get('DestinationUniqueKey')
        if destkey is not None:
            attribs = attribs_from_destkey(elem, destkey, **params)
        else:
            # use the hyperlink properties to create the link    
            d = h.find("Properties/Destination[@type='object']")
            if d is not None:
                # if DEBUG==True: print("property dest:", d.attrib)
                if 'HyperlinkTextDestination/' in d.text:
                    tds = elem.xpath("//HyperlinkTextDestination[@Self='%s']" % d.text)
                    if len(tds) == 1:
                        attribs.anchor = make_anchor_name(tds[0].get('Name'))
                    elif len(tds) == 0 and params.get('documents') is not None:
                        # look in params['documents']
                        for doc in params['documents']:
                            tds = doc.root.xpath("//HyperlinkTextDestination[@Self='%s']" % d.text)
                            if len(tds) == 1:
                                relpath = os.path.relpath(doc.fn, os.path.dirname(params['fn']))
                                attribs.filename = os.path.splitext(relpath)[0] + '.xml'
                                attribs.anchor = make_anchor_name(tds[0].get('Name'))
                elif 'HyperlinkURLDestination/' in d.text:
                    uu = elem.xpath("//HyperlinkURLDestination[@Self='%s']" % d.text)
                    if len(uu) == 1:
                        attribs.filename = uu[0].get('DestinationURL')
    # if DEBUG==True: print(elem.attrib, '=>', attribs)
    return attribs

def attribs_from_destkey(elem, destkey, **params):
    attribs = Dict()
    doc = None
    dest_xpath = """//*[contains(name(), 'Hyperlink') and contains(name(), 'Destination') 
        and @DestinationUniqueKey='%s']""" % destkey
    # first look in the current document
    dest = XML.find(elem, dest_xpath)
    # then look in params documents
    if dest is None:
        for doc in (params['documents'] or []):
            dest = XML.find(doc.root, dest_xpath)
            if dest is not None: 
                break
    if dest is not None:
        if dest.tag=='HyperlinkURLDestination':
            attribs.filename = dest.get('DestinationURL')
        elif dest.tag=='HyperlinkTextDestination':
            attribs.anchor = make_anchor_name(dest.get('Name'))
            if doc is not None and doc.fn != params['fn']:
                # replace ' ' with '_' in xml filename
                path, base = os.path.split(os.path.splitext(doc.fn)[0])
                base = re.sub('[^0-9A-Za-z\.\-\_]', '_', base)+'.xml'
                newfn = '/'.join([path, base])
                attribs.filename = os.path.basename(newfn)
        elif dest.tag=='ParagraphDestination':
            attribs.anchor = make_anchor_name(dest.get('Name'))
    return attribs

# == HyperlinkTextSource  or CrossReferenceSource ==
@transformer.match("elem.tag in ['HyperlinkTextSource', 'CrossReferenceSource']")
def HyperlinkTextOrCrossReferenceSource(elem, **params):
    anchor_name = String(elem.get('Name')).identifier()
    anchor_start = B.pub.anchor_start(name=anchor_name)
    anchor_end = B.pub.anchor_end(name=anchor_name)
    attribs = hyperlink_attribs(elem, source=elem.get('Self'), **params)
    if attribs is not None:
        hyperlink = B.pub.hyperlink(attribs, transformer(elem.getchildren(), **params))
        cc = hyperlink.getchildren()
        if len(cc)==1 and cc[0].tag=="{%(pub)s}cref" % NS:
            for k in hyperlink.attrib.keys():
                cc[0].set(k, hyperlink.get(k))
            return cc
        else:
            return [anchor_start, hyperlink, anchor_end]
    else:
        return []

# == TextVariableInstance == 
@transformer.match("elem.tag=='TextVariableInstance'")
def TextVariableInstance(elem, **params):
    text_variable = XML.find(elem, "//TextVariable[@Self='%s']" % elem.get('AssociatedTextVariable'))
    # if text_variable is not None:
    #     variable_type = text_variable.get('VariableType')
    #     if variable_type == 'XrefPageNumberType':
    #         # page references 
    #         return [B.pub.cref(elem.get('ResultText'))]
    #     elif variable_type == 'ModificationDateType':
    #         return [B.pub.modified(elem.get('ResultText') or '', idformat=text_variable.find('DateVariablePreference').get('Format'))]
    #     else:
    #         return [elem.get('ResultText')]
    # else:
    #     return [elem.get('ResultText')]
    log.debug("%s %r %r" % (elem.tag, elem.attrib, elem.get('ResultText')))
    return [B.pub.textvariable(elem.get('ResultText'), **elem.attrib)]

# == Rectangle == 
@transformer.match("elem.tag=='Rectangle'")
def Rectangle(elem, **params):
    return transformer(elem.getchildren(), **params)

@transformer.match("elem.tag in ['PDF', 'Image']")
def PDF_or_Image(elem, **params):
    link = elem.find("Link")
    if link is not None and link.get("LinkResourceURI") is not None:
        url = URL(link.get("LinkResourceURI"))
        filename = os.path.join(
            'Links',
            re.sub("(&[\w^;]+;|[\s\&+;'])", "-", os.path.basename(str(url))) + '.jpg')
    else:
        filename=None
    return [B.pub.image(filename=filename)]

# == XML Element == 
@transformer.match("elem.tag=='XMLElement'")
def XMLElement(elem, **params):
    e = Builder()._(
            elem.get('MarkupTag').split('/')[-1],
            transformer(elem.getchildren(), **params))
    for attr in elem.xpath("XMLAttribute"):
        if 'xmlns:' not in attr.get('Name'):
            e.set(attr.get('Name'), attr.get('Value'))
    return [e]

# == TextFrame == 
@transformer.match("elem.tag=='TextFrame'")
def TextFrame(elem, **params):
    return [B.pub.include(id=elem.get('ParentStory'))]

# == Processing Instructions == 
@transformer.match("type(elem)==etree._ProcessingInstruction")
def ProcessingInstruction(elem, **params):
    pitext = etree.tounicode(elem).strip("<?>") 
    if pitext[:5] == 'ACE 4':
        r = [B.pub.footnote_ref()]
    elif pitext[:5] in ['ACE 7', 'ACE 8']:
        r = ['\t']
    else:
        r = []
    return r + [elem.tail]

# == Changes == 
@transformer.match("elem.tag=='Change'")
def Change(elem, **params):
    """Deal with redlining. For now, just provide the results. Later, we'll support the HTML <ins> and <del> tags.
    """
    # attrib = dict(
    #     datetime=elem.get('Date'),
    #     title="user=%r" % elem.get('UserName').replace('$ID/',''),
    # )
    if elem.get('ChangeType') in ['InsertedText', 'MovedText']:
        # res = B.html('ins', attrib, transformer(elem.getchildren(), **params))
        return transformer(elem.getchildren(), **params)
    elif elem.get('ChangeType')=='DeletedText':
        # res = B.html('del', attrib, transformer(elem.getchildren(), **params))
        pass
    else:
        log.warn("Invalid ChangeType: %r" % elem.get('ChangeType'))

# == omitted/ignored == 
omitted = [
    'Bookmark', 'Cell', 'Color', 'ColorGroup', 'Column', 'CompositeFont', 'CrossReferenceFormat', 
    'DocumentUser', 'FontFamily', 'FrameFittingOption', 'Group', 'Hyperlink', 'HyperlinkURLDestination', 
    'InCopyExportOption', 'Ink', 'MetadataPacketPreference', 'NumberingList', 'ObjectExportOption',
    'Properties', 'RootCellStyleGroup', 'RootCharacterStyleGroup', 'RootObjectStyleGroup',
    'RootParagraphStyleGroup', 'RootTableStyleGroup', 'StandaloneDocumentPreference', 
    'StoryPreference', 'StrokeStyle', 'Swatch', 'TextWrapPreference',
    'TinDocumentDataObject', 'TransparencyDefaultContainerObject', 'Condition', 'TextVariable',
    'KinsokuTable', 'MojikumiTable', 'XMLAttribute', 'AnchoredObjectSetting', 'Polygon'
]
@transformer.match("elem.tag in %s" % str(omitted))
def omissions(elem, **params):
    return transformer.omit(elem, keep_tail=False, **params)

# == default == 
@transformer.match("True")
def default(elem, **params):
    return [transformer.copy(elem, **params)]

def pre_process(doc, **params):
    # doc = embed_textframes(doc)
    doc = convert_tabs(doc)
    return doc

def post_process(doc, **params):
    doc = convert_line_breaks(doc)
    doc = remove_empty_spans(doc)
    doc = process_t_codes(doc)
    doc = process_endnotes(doc)
    doc = hyperlinks_inside_paras(doc)
    doc = unpack_nested_paras(doc)
    doc = anchors_shift_paras(doc)
    doc = anchors_outside_hyperlinks(doc)
    doc = anchors_inside_paras(doc)
    doc = remove_empty_paras(doc)
    doc = fix_endnote_refs(doc)
    doc = p_tails(doc)
    # doc = includes_before_paras(doc)
    return doc

def embed_textframes(doc):
    for textframe in doc.xpath("//TextFrame[@ParentStory]"):
        textframe_stories = doc.xpath("//Story[@Self='%s']" % textframe.get('ParentStory'))
        if len(textframe_stories) < 1: continue
        textframe_story = textframe_stories[0]
        parent = textframe.getparent()
        while parent.tag in ['ParagraphStyleRange', 'CharacterStyleRange']:
            XML.unnest(textframe)
            parent = textframe.getparent()
        for e in textframe_story.getchildren():
            parent.insert(parent.index(textframe), e)
        parent.remove(textframe)
        textframe_story.getparent().remove(textframe_story)
    return doc

def convert_tabs(doc):
    txt = etree.tounicode(doc)
    txt = txt.replace("<?ACE 8?>", "<pub:tab align='right' xmlns:pub='%(pub)s'/>" % NS)
    txt = txt.replace("<?ACE 7?>", "")                                          # align "here" tab
    tfn = os.path.join(os.path.dirname(__file__), random_id())
    with open(tfn, 'wb') as tf:
        tf.write(txt.encode('utf-8'))
    d = etree.parse(tfn).getroot()
    os.remove(tfn)
    return d

def remove_empty_spans(doc):
    for span in doc.xpath("//html:span", namespaces=NS):
        if span.attrib.keys() == [] or XML.is_empty(span, ignore_whitespace=True):
            XML.replace_with_contents(span)
    return doc

def process_t_codes(doc):
    body = doc.find("{%(html)s}body" % NS)
    for t in doc.xpath("//pub:t", namespaces=NS):
        XML.replace_with_contents(t)
    return doc

def convert_line_breaks(doc):
    txt = etree.tounicode(doc)
    txt = txt.replace('\u2028', '<br/>')        # forced line break
    txt = txt.replace('\u200b', '')             # discretionary line break / zero-width space
    return etree.fromstring(txt.encode('utf-8'))

def process_endnotes(doc):
    # enclose endnotes that are tagged with endnote_start
    for e in doc.xpath("//html:endnote_start", namespaces=NS):
        e.tag = "{%(pub)s}endnote" % NS
        nxt = e.getnext()
        while nxt is not None and nxt.tag != "{%(pub)s}endnote_start" % NS:
            e.append(nxt)
            nxt = e.getnext()

    # for now, just strip off the endnote characteristics so that HTML output can be processed
    for endnote in doc.xpath("//html:endnote", namespaces=NS):
        endnote.text = endnote.tail = None
        XML.replace_with_contents(endnote)
    for ie in doc.xpath("//html:insert_endnotes", namespaces=NS):
        XML.replace_with_contents(ie)
    return(doc)     

def hyperlinks_inside_paras(doc):
    "hyperlinks that cross paragraph boundaries need to be nested inside the paragraphs"
    for hyperlink in doc.xpath("//html:hyperlink[html:p]", namespaces=NS):
        XML.interior_nesting(hyperlink, "html:p", namespaces=NS)
    return doc

def unpack_nested_paras(doc):
    """HiddenText (conditional text) often results in nested paras, they need to be unpacked"""
    for p in doc.xpath("//html:p/html:p", namespaces=NS):
        XML.unnest(p)
    return doc

def remove_empty_paras(doc):
    """empty paras are meaningless and removed."""
    for p in doc.xpath(".//html:p", namespaces=NS):
        XML.remove_if_empty(p, leave_tail=False, ignore_whitespace=False)
    return doc  

def p_tails(doc):
    for p in doc.xpath(".//html:p", namespaces=NS):
        p.tail = '\n'
    return doc  

def includes_before_paras(doc):
    for include in doc.xpath(".//pub:include", namespaces=NS):
        p = XML.find(include, "ancestor::html:p", namespaces=NS)
        if p is not None:
            parent = p.getparent()
            parent.insert(parent.index(p), include)
            include.tail = '\n'
    return doc

def anchors_shift_paras(doc):
    # a monstrosity
    for p in doc.xpath("//html:p", namespaces=NS):
        while len(p.getchildren()) > 0 \
        and p.text in [None, ''] \
        and p.getchildren()[0].tag in ["{%(pub)s}anchor_start" % NS, "{%(pub)s}anchor_end" % NS]:
            a = p.getchildren()[0]
            while a is not None and a.tag == "{%(pub)s}anchor_start" % NS and a.tail in [None, '']:
                a = a.getnext()
            if a is None or a.tag != "{%(pub)s}anchor_end" % NS: 
                break
            prevs = p.xpath("preceding::html:p", namespaces=NS)
            if len(prevs) > 0:
                prev = prevs[-1]
                while prev is not None and len(prev.getchildren()) == 0 and prev.text in [None, '']:
                    prevs = prev.xpath("preceding::html:p", namespaces=NS)
                    if len(prevs) == 0: break
                    prev = prevs[-1]
                if prev is not None:
                    XML.remove(a, leave_tail=True)
                    a.tail = ''
                    prev.append(a)
            else:
                break
        while len(p.getchildren()) > 0 \
        and p.getchildren()[-1].tag == "{%(pub)s}anchor_start" % NS\
        and p.getchildren()[-1].tail in [None, '']:
            a = p.getchildren()[-1]
            nexts = p.xpath("following::html:p", namespaces=NS)
            if len(nexts) > 0:
                XML.remove(a, leave_tail=True)
                nexts[0].insert(0, a)
                if nexts[0].text not in [None, '']:
                    nexts[0].text, a.tail = '', nexts[0].text
            else:
                break
    return doc

def anchors_outside_hyperlinks(doc):
    "make sure anchors are outside of hyperlinks"
    for a in doc.xpath("//html:anchor_start[ancestor::html:hyperlink]", namespaces=NS):
        h = a.xpath("ancestor::html:hyperlink", namespaces=NS)[0]
        XML.remove(a); a.tail = ''
        parent = h.getparent()
        parent.insert(parent.index(h), a)
    for a in doc.xpath("//html:anchor_end[ancestor::html:hyperlink]", namespaces=NS):
        h = a.xpath("ancestor::html:hyperlink", namespaces=NS)[0]
        XML.remove(a); a.tail = ''
        parent = h.getparent()
        parent.insert(parent.index(h)+1, a)
    return doc

def anchors_inside_paras(doc):
    """anchor_start at the start of the next para, anchor_end at the end of the previous para"""
    for anchor_start in doc.xpath("//html:anchor_start[not(ancestor::html:p)]", namespaces=NS):
        paras = anchor_start.xpath("following::html:p", namespaces=NS)
        if len(paras) > 0:
            para = paras[0]
            XML.remove(anchor_start, leave_tail=True)
            para.insert(0, anchor_start)
            anchor_start.tail, para.text = para.text, ''
    for anchor_end in doc.xpath("//html:anchor_end[not(ancestor::html:p)]", namespaces=NS):
        paras = anchor_end.xpath("preceding::html:p", namespaces=NS)
        if len(paras) > 0:
            para = paras[-1]
            XML.remove(anchor_end, leave_tail=True)
            para.append(anchor_end)
    return doc    

def fix_endnote_refs(doc):
    "make sure endnote references are superscript"
    for hyperlink in doc.xpath("//html:hyperlink[not(ancestor::html:span) and not(html:span) and contains(@anchor, 'endnote_ref_')]", namespaces=NS):
        span = B.html.span({'class':"_Endnote Reference"})
        span.text, hyperlink.text = hyperlink.text or '', ''
        for ch in hyperlink.getchildren():
            span.append(ch)
        hyperlink.insert(0, span)
    return doc

def process_para_breaks(body):
    # If a <pub:p_break/> is in the midst of a <p>, make a new <p>. 
    for p_break in body.xpath(".//pub:p_break", namespaces=NS):
        p = p_break.xpath("ancestor::html:p", namespaces=NS)[-1]
        parent = p_break.getparent()
        while parent != p:
            XML.unnest(p_break)
            parent = p_break.getparent()
            assert parent != body
        XML.unnest(p_break)
        XML.remove(p_break)
    return body  

def nest_span_hyperlinks(body):
    # span must nest within hyperlink
    for span in body.xpath("//html:span[html:hyperlink]", namespaces=NS):
        XML.fragment_nesting(span, "html:hyperlink", namespaces=NS)
    return body   

def split_sections(body):
    """convert pub:section_start tags into html:section elements"""
    sections = XML.xpath(body, ".//pub:section_start", namespaces=NS)
    for section in sections:
        section.tag = "{%(html)s}section" % NS
        section.text = '\n'
        next = section.getnext()
        while next is not None and next.tag != "{%(pub)s}section_start" % NS:
            elem = next
            next = elem.getnext()
            section.append(elem)
    return body

def is_prev_node_br(elem):
    prev = elem.getprevious()
    if prev is not None and prev.tag == 'Br':
        return True
    else:
        # TODO: figure out how to do this properly with xpath
        parent = elem.xpath("..")
        if len(parent) > 0:
            prev_parent = parent[0].getprevious()
            if prev_parent is not None:
                p_children = prev_parent.getchildren()
                if len(p_children) > 0:
                    if p_children[-1].tag == 'Br':
                        return True
    return False

