
import re, json, os, sys
from glob import glob
from lxml import etree
import urllib.parse
from bl.dict import Dict
from bl.id import random_id
from bl.string import String
from bxml.xml import XML
from bxml.xt import XT
from bxml.builder import Builder

import pubxml
from pubxml.converters import Converter
from pubxml.document import Document
from pubxml.icml import ICML

B = Builder(**pubxml.NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocumentIcml(Converter):
    def convert(self, document, **params):
        return document.transform(transformer, XMLClass=ICML, **params)

@match(transform, "elem.tag == '{%(pub)s}document'" % pubxml.NS)
def document(elem, **params):
    # using procedural code to build doc as ElementTree so as to keep the PIs in place.
    doc = etree.ElementTree(etree.fromstring("""\
<?aid style="50" type="snippet" readerVersion="6.0" featureSet="257" product="9.2(103)" ?>
<?aid SnippetType="InCopyInterchange"?>
<Document DOMVersion="8.0" Self="d">\n\t</Document>
"""))
    root = doc.getroot()

    if params.get('mutable') is None: 
        params['mutable'] = Dict()

    # collector for hyperlinks (to be appended to the document at the end)
    if params.get('Hyperlinks') is None: params['Hyperlinks'] = []

    # collector for endnotes 
    # (to be inserted wherever "insert_endnotes" appears, or in a separate .icml document)
    if params['mutable'].get('Endnotes') is None: params['mutable']['Endnotes'] = []

    # collector for bookmarks
    if params.get('Bookmarks') is None: params['Bookmarks'] = []

    elem = pre_process_source(elem)

    # transform the document
    for ch in transform(list(elem), **params):
        if type(ch)!=str:
            root.append(ch) 

    story = root.find("Story")

    # RootCharacterStyleGroup
    charstyles = [charstyle for charstyle in 
                    list(set([c.get('AppliedCharacterStyle') for c in story.xpath(".//CharacterStyleRange")]))
                    if charstyle is not None and charstyle.strip() != '']
    rcsg = E.RootCharacterStyleGroup(
            {'Self': 'rcsg'},
            '\n\t\t',
            [E.CharacterStyle(
                {'Self': charstyle, 'Name': urllib.parse.unquote(charstyle.replace("CharacterStyle/",''))}
                ) for charstyle in charstyles],
            '\n\t\t'
        ); rcsg.tail='\n\t'
    if params.get('charstyles') is not None:
        # a list of CharacterStyle definitions was given -- insert into rpsg
        for charstyle in params.get('charstyles'):
            existing_charstyle = rpsg.find("CharacterStyle[@Name='%s']" % charstyle.get('Name'))
            if existing_charstyle is not None:
                rpsg.replace(existing_charstyle, charstyle)
            else:
                rpsg.append(charstyle)
    root.insert(root.index(story), rcsg)

    # RootParagraphStyleGroup
    parastyles = [parastyle for parastyle in 
                    list(set([p.get('AppliedParagraphStyle') for p in story.xpath(".//ParagraphStyleRange")]))
                    if parastyle is not None and parastyle.strip() != '']
    rpsg = E.RootParagraphStyleGroup(
            {'Self': 'rpsg'},
            '\n\t\t',
            [E.ParagraphStyle(
                {'Self': parastyle, 'Name': urllib.parse.unquote(parastyle.replace("ParagraphStyle/",''))}
                ) for parastyle in parastyles],
            '\n\t\t'
        ); rpsg.tail='\n\t'
    if params.get('parastyles') is not None:
        # a list of ParagraphStyle definitions was given -- insert into rpsg
        for parastyle in params.get('parastyles'):
            existing_parastyle = rpsg.find("ParagraphStyle[@Name='%s']" % parastyle.get('Name'))
            if existing_parastyle is not None:
                rpsg.replace(existing_parastyle, parastyle)
            else:
                rpsg.append(parastyle)
    root.insert(root.index(story), rpsg)

    # docvars
    docvar_elems = elem.xpath("c:docvars/c:docvar", namespaces=pubxml.NS)
    docvars = {e.get('name'):e.get('value') for e in docvar_elems}
    if len(docvars) > 0:    
        code = "{{docvars}}%s{{/docvars}}" % json.dumps(docvars)
        note = Note(code); note.tail = '\n'
        story.insert(0, note)
    
    # CrossReferenceFormats
    crf = E.CrossReferenceFormat({'Self': 'PageNumberCrossReferenceFormat'},
            '\n\t\t',
            E.BuildingBlock(
                {'Self': 'PageNumberCrossReferenceFormatBuildingBlock01',
                'BlockType': 'PageNumberBuildingBlock'}),
            '\n\t'); crf.tail='\n\t'
    root.insert(root.index(root.find('Story')), crf)
    crf = E.CrossReferenceFormat({'Self': 'ParagraphNumberCrossReferenceFormat'},
            '\n\t\t',
            E.BuildingBlock(
                {'Self': 'ParagraphNumberCrossReferenceFormatBuildingBlock01',
                'BlockType': 'ParagraphNumberBuildingBlock'}),
            '\n\t'); crf.tail='\n'
    root.insert(root.index(root.find('Story')), crf)
    crf = E.CrossReferenceFormat({'Self': 'ParagraphTextCrossReferenceFormat'},
            '\n\t\t',
            E.BuildingBlock(
                {'Self': 'ParagraphTextCrossReferenceFormatBuildingBlock01',
                'BlockType': 'ParagraphTextBuildingBlock'}),
            '\n\t'); crf.tail='\n'
    root.insert(root.index(root.find('Story')), crf)

    # Condition definitions: Print and Digital
    root.insert(root.index(root.find('Story')), 
        condition_definition('Print', 'GridGreen'))
    root.insert(root.index(root.find('Story')), 
        condition_definition('Digital', 'GridBlue'))

    # TextVariables: Timestamp
    root.insert(root.index(root.find('Story')), 
        E.TextVariable({
            'Self': 'TimestampTextVariable',
            'Name': 'Timestamp',
            'VariableType': 'ModificationDateType'
            },
            E.DateVariablePreference({
                'TextBefore': '',
                'TextAfter': '',
                'Format': 'yyyy-MM-dd hh:mm a'
                })))
    
    # Hyperlinks
    for h in params['Hyperlinks']:
        root.append(h)

    # Bookmarks
    for b in params['Bookmarks']:
        root.append(b)

    # Place any remaining endnotes in a new ICML document named *_Endnotes.xml
    if len(params['mutable']['Endnotes']) > 0:
        endnotes_doc = XML(root=document(B.pub('document', B.html('body', B.html('section', *params['mutable']['Endnotes']))))[0],
                            fn=os.path.splitext(params.get('fn'))[0] + '_Endnotes.xml')
        endnotes_doc.write()
        params['mutable']['Endnotes'] = []

    return [doc]

def pre_process_source(elem):
    s = etree.tounicode(elem)
    s = s.replace('<br/>', '\u2028')    # line-break codes to soft-return characters
    e = etree.fromstring(s)
    e = transformer_XSLT(e).getroot()
    return e

def condition_definition(name, color):
    e =  E.Condition(
            {'Self':"Condition/"+name, 'Name':name,
            'IndicatorMethod':'UseHighlight', 'Visible':'true'},
            E.Properties(E.IndicatorColor({'type':'enumeration'}, color)))
    e.tail = '\n\t'
    return e

@match(transform, "elem.tag=='{%(html)s}body'" % pubxml.NS)
def body(elem, **params):
    params['story_id'] = 's'+random_id(6)               # to use in building unique sequential ids, such as Hyperlinks
    story = E.Story({'Self': params['story_id']}, '\n',
                transform(list(elem), **params)
            )
    story.tail='\n'
    return [story]

@match(transform, "elem.tag=='{%(html)s}section'" % pubxml.NS)
def section(elem, **params):
    attrib_string = ' '.join(['%s="%s"' % (k, elem.get(k)) for k in elem.attrib.keys()])
    r = [
        # '\n', 
        # Note("{{section_start %s/}}" % attrib_string), '\n',
    ] + transform(list(elem), **params) + [
        # '\n',
        # Note("{{/section}}"), '\n'
    ]

    # put a hard page break of the correct kind, if called for by the section break
    sections = elem.xpath("//c:section", namespaces=pubxml.NS)
    if elem.get('break_type')=='nextPage':
        r = page_break(elem, break_type='Next') + r
    elif elem.get('break_type')=='oddPage':
        r = page_break(elem, break_type='Odd') + r
    elif elem.get('break_type')=='evenPage':
        r = page_break(elem, break_type='Even') + r
    # else break_type == 'continuous', no page_break() inserted

    return r

# == Element Functions == 

def CharacterStyleRange(*args, **params):
    kwargs = {}
    if params.get('AppliedConditions') is not None:
        kwargs['AppliedConditions'] = params['AppliedConditions']
    if params.get('charstyle') is not None:
        stylename = String(params.get('charstyle')).strip("_").camelify()
        stylename = urllib.parse.quote(str(stylename))
    else:
        stylename = '$ID/[No character style]'
        params['charstyle'] = stylename
    charstyle = 'CharacterStyle/'+stylename
    return E.CharacterStyleRange(
            {'AppliedCharacterStyle': charstyle},
            '\n\t\t',
            *args,
            **kwargs
        )

def TextContentCSR(text, **params):
    if text not in [None, '']:
        return CharacterStyleRange(E.Content(text), '\n\t', **params)
    else:
        return ''

def Note(text):
    return E.Note('\n\t\t\t', 
        E.ParagraphStyleRange('\n\t\t\t\t', 
            E.CharacterStyleRange('\n\t\t\t\t\t', 
                E.Content(text), '\n\t\t\t\t'), 
            '\n\t\t\t'), 
        '\n\t\t')

def ElemToCode(elem):
    return etree.tounicode(elem, with_tail=False).replace("<", "{{").replace(">", "}}")

# == PARA and CHAR == 

@match(transform, "elem.tag=='{%(html)s}p'" % pubxml.NS)
def para(elem, **params):
    # if insert_endnotes occurs in this paragraph, just do that
    if elem.find("{%(pub)s}insert_endnotes" % pubxml.NS) is not None:
        return transform(list(elem), **params)

    if elem.get('style') is not None:
        stylename = String(elem.get('style')).strip("_").camelify()
        stylename = urllib.parse.quote(str(stylename))
    else:
        stylename = '$ID/[No paragraph style]'
    parastyle = "ParagraphStyle/"+stylename

    p = E.ParagraphStyleRange(
            {'AppliedParagraphStyle': parastyle},
            '\n\t', 
            TextContentCSR(elem.text, **params),
            transform(list(elem), **params),
            '\n\t', 
            CharacterStyleRange(E.Br(), '\n\t', **params),
            '\n'
        )
    p.tail = '\n'

    # if the para has outline="1", add a destination and bookmark
    if elem.get('outline')=='1':
        txt = etree.tounicode(elem, method='text', with_tail=False).strip()
        prevs = elem.xpath("preceding::c:para", namespaces=pubxml.NS)
        if len(prevs) > 0:
            prev = prevs[-1]
        else:
            prev = None
        # merge consecutive outline="1" elements into the first one. So check in both directions.
        if prev is None or prev.tag != "{%(html)s}para" % pubxml.NS or prev.get('outline') != '1':
            # only insert a bookmark if the previous paragraph was not outline="1"

            # merge the following outline="1" paras into this bookmark
            nxt = elem.getnext()
            while nxt is not None and nxt.tag=="{%(html)s}para" % pubxml.NS and nxt.get('outline')=='1':
                txt += ' ' + etree.tounicode(nxt, method='text', with_tail=False).strip()
                nxt = nxt.getnext()

            # use a child anchor_start if there is no text before it in the element
            # -- bookmark needs to hit the beginning of the paragraph in case there's a turn-over
            anchors = elem.xpath("c:anchor_start", namespaces=pubxml.NS)
            if len(anchors) > 0 and elem.text in [None, ''] \
            and ''.join([
                        etree.tounicode(e, method='text',with_tail=True) 
                        for e in anchors[0].xpath("preceding-sibling::*")
                        ]) == '':
                destname = anchors[0].get('name')
            else:
                destname = re.sub('[^0-9A-Za-z\.\-\_]', '_', txt[:30].strip()).strip("_") + '_1_1'
                if re.search("^\d", destname) is not None:
                    destname = '_' + destname
                dest = HyperlinkTextDestination(destname)
                p.insert(0, CharacterStyleRange(dest, **params))
            params['Bookmarks'].append(Bookmark(txt, destname))
    return [p]

def destination_name():
    pass

def Bookmark(bkmkname, destname):
    b = E.Bookmark(Self=random_id(), Name=bkmkname, Destination='HyperlinkTextDestination/'+destname)
    b.tail='\n\t'
    return b

@match(transform, "elem.tag=='{%(html)s}char'" % pubxml.NS)
def char(elem, **params):
    csr = CharacterStyleRange(
            transform(list(elem), charstyle=elem.get('style'), **params), 
            '\n\t',
            charstyle=elem.get('style'), 
            **params)
    if elem.text not in ['', None]:
        csr.insert(0, E.Content(elem.text))
    return [
        csr,
        TextContentCSR(elem.tail, **params)
    ]

# == TABLES == 

@match(transform, "elem.tag=='{%(html)s}table'" % pubxml.NS)
def table(elem, **params):
    trs = elem.xpath("c:tr", namespaces=pubxml.NS)
    numrows = len(trs)
    numcols = len(elem.xpath("c:tr[1]/c:td", namespaces=pubxml.NS))
    colwidth = 324 / numcols           # 324 points = 4.5 inches as the total width of the table
    tblName = 't'+random_id(8)
    tbl = E.Table(
            {'Self': tblName, 'BodyRowCount': str(numrows), 'ColumnCount': str(numcols)},
            '\n\t\t\t',
            [E.Row({'Name': str(i), 'Self': tblName+'Row'+str(i)}) for i in range(numrows)],
            '\n\t\t\t',
            [E.Column({'Name': str(i), 'Self': tblName+'Column'+str(i), 
                        'SingleColumnWidth': "%d" % colwidth}) 
                for i in range(numcols)],
            '\n\t\t\t'
        )    
    c = 0
    for tr in trs:
        tds = tr.xpath("c:td", namespaces=pubxml.NS)
        for td in tds:
            c += 1
            cell = E.Cell(
                {'Name': "%d:%d" % (tds.index(td), trs.index(tr)),
                'Self': tblName+'i'+str(c)},
                '\n',
                transform(td.getchildren(), **params))
            cell.tail='\n\t\t\t'
            ch = cell.getchildren()
            if len(ch) > 0: 
                ch[-1].tail+='\t\t\t'
                br = cell.xpath(".//Br")[-1]
                parent = br.getparent()
                parent.remove(br)
                if len(parent.getchildren())==0:
                    parent.getparent().remove(parent)
            tbl.append(cell)
    p = E.ParagraphStyleRange(
            {'AppliedParagraphStyle': 'ParagraphStyle/$ID/[No paragraph style]'},
            '\n\t',
            CharacterStyleRange(tbl, '\n\t', **params),
            '\t'
        )
    return [p, '\n']

# == Footnotes == 

@match(transform, "elem.tag=='{%(pub)s}footnote'" % pubxml.NS)
def footnote(elem, **params):
    # don't pass down the character style of the enclosing <char>
    fn_params = {k:params[k] for k in params.keys() if k != "charstyle"}
    fn = E.Footnote('\n', 
            transform(list(elem), **fn_params),
            '\n\t\t')
    # the last paragraph in a footnote doesn't need a <Br/> at the end
    brs = fn.xpath("ParagraphStyleRange[last()]/CharacterStyleRange[last()]/Br[last()]")
    if len(brs) > 0:
        brs[-1].getparent().remove(brs[-1])
    res = ['\n\t\t', fn]
    # Notes in footnotes (usually index entries) have to be moved outside the footnote
    for index_entry in fn.xpath(".//Note"):
        res.insert(0, index_entry)
        res.insert(0, '\n\t\t')
    return res

@match(transform, "elem.tag=='{%(pub)s}footnote_ref'" % pubxml.NS)
def footnote_ref(elem, **params):
    return ['\n\t\t', E.Content(etree.PIBase('ACE 4'))]

# == Endnotes == 
# section @endnote_fmt in ['decimal', 'lowerLetter', 'upperLetter', 'lowerRoman', 'upperRoman', 'chicago']

@match(transform, "elem.tag=='{%(pub)s}endnote'" % pubxml.NS)
def endnote(elem, **params):
    # give endnote a unique id in the publication by using the story id.
    endnote_id = "endnote_" + elem.get('id') + "_" + params['story_id']
    endnote_ref_id = endnote_id.replace('endnote_', 'endnote_ref_')
    endnote_marker = build_endnote_marker(elem)
    source_id = random_id(8)
    params['mutable']['Endnotes'] += \
        transform(list(elem), endnote_id=endnote_id,
            **{k:params[k] for k in params.keys() if k != "charstyle"})

    params['Hyperlinks'].append(
        paragraph_destination(source_id, anchor=endnote_id, **params))    
    
    e = E.CrossReferenceSource(
            {'Self': source_id,
             'Name': endnote_ref_id,
            'AppliedFormat': 'ParagraphNumberCrossReferenceFormat'},
            E.Content(endnote_marker)
        )
    return [e]

def paragraph_destination(source_id, anchor, **params):
    hyperlink_id = random_id(8)
    h = E.Hyperlink({'Self': hyperlink_id, 
                    'Source': source_id, 
                    'Name': "Cross-Reference %s" % hyperlink_id},
            E.Properties(E.Destination({'type':'object'}, "ParagraphDestination/"+anchor))
        ); h.tail = '\n'
    return h


# def endnote(elem, **params):
#     # collect the endnote into params['mutable']['Endnotes'], to be output at insert_endnotes or a separate document.
#     # number the endnote according to the parameters of the enclosing section.
#     # hyperlink from the endnote reference to the endnote and back. (hyperlinking across stories?)
    
#     # give endnote a unique id in the publication by using the story id.
#     endnote_id = "endnote_" + elem.get('id') + "_" + params['story_id']
#     endnote_marker = build_endnote_marker(elem)

#     # add the endnote output to params['mutable']['Endnotes']
#     # don't pass down the character style of the enclosing <char>
#     en_params = {k:params[k] for k in params.keys() if k != "charstyle"}
#     endnote_ref_id = endnote_id.replace('endnote_', 'endnote_ref_')
#     params['mutable']['Endnotes'] += [
#         Note("{{endnote_start id='%s'/}}" % elem.get('id')),
#     ] + transform(list(elem), 
#             endnote_marker=endnote_marker, 
#             endnote_id=endnote_id, 
#             endnote_ref_id=endnote_ref_id, 
#             **en_params) + [
#         # Note("{{/endnote}}")
#     ]
    
#     # return the endnote_ref to the document tree here
#     source_id = random_id(8)
#     params['Hyperlinks'].append(
#         hyperlink_destination(source_id, anchor=endnote_id, **params))

#     return [
#         HyperlinkTextDestination(endnote_ref_id),
#         HyperlinkTextSource(source_id, endnote_marker, [], **params),
#         HyperlinkTextDestination(endnote_ref_id + "_end")
#     ]

def build_endnote_marker(elem):
    """returns the correct endnote marker for this endnote"""
    section = elem.xpath("ancestor::c:section", namespaces=pubxml.NS)[0]
    endnote_fmt = section.get('endnote_fmt') or 'lowerLetter'       # default lowerLetter?
    endnote_base = int(section.get('endnote_start') or "1") - 1     # base = starting number - 1

    # endnote index
    if section.get('endnote_renum') == 'eachSect':      # index in section
        index = section.xpath(".//c:endnote", namespaces=pubxml.NS).index(elem)
    else:                                               # index in document
        index = elem.xpath("//c:endnote", namespaces=pubxml.NS).index(elem)
    index += endnote_base
    
    # endnote marker
    if endnote_fmt == 'decimal':
        endnote_marker = str(index + 1)
    elif endnote_fmt[-6:] == 'Letter':
        letters = "abcdefghijklmnopqrstuvwxyz"
        endnote_marker = letters[index % len(letters)] * (index // len(letters) + 1)
        if endnote_fmt[:5] == 'upper':
            endnote_marker = endnote_marker.upper()
    elif endnote_fmt[-5:] == 'Roman':
        from be.integer import to_roman
        endnote_marker = to_roman(index + 1)    # uppercase roman numeral
        if endnote_fmt[:5] == 'lower':
            endnote_marker = endnote_marker.lower()
    elif endnote_fmt == 'chicago':
        chicago = "*\u2020\u2021\u00a7"     # four characters: asterisk, cross, double-cross, section symbol
        endnote_marker = chicago[index % len(chicago)] * (index // len(chicago) + 1)
    return endnote_marker


@match(transform, "elem.tag=='{%(pub)s}endnote_ref'" % pubxml.NS)
def endnote_ref(elem, endnote_id=None, **params):
    d = E.ParagraphDestination(Self="ParagraphDestination/"+endnote_id, Name=endnote_id)
    return [d, TextContentCSR(elem.tail, **params)]

@match(transform, "elem.tag=='{%(pub)s}insert_endnotes'" % pubxml.NS)
def insert_endnotes(elem, **params):
    # insert the collected endnotes at the <insert_endnotes/>
    # and reset params['mutable']['Endnotes'] for further endnote collecting.
    endnotes = [
        # Note("{{insert_endnotes}}")
        ] + params['mutable']['Endnotes'] + [
        # Note("{{/insert_endnotes}}")
        ]
    params['mutable']['Endnotes'] = []
    return endnotes

# == Print and Digital == 
@match(transform, "elem.tag in ['{%(pub)s}print', '{%(pub)s}digital']" % pubxml.NS)
def condition_elem(elem, **params):
    params['AppliedConditions'] = 'Condition/' + String(elem.tag.replace("{%(pub)s}" % pubxml.NS, '')).titleify()
    return [TextContentCSR(elem.text, **params)] \
        + transform(list(elem), **params) \
        +  [TextContentCSR(elem.tail, **params)]

# == Anchors and Hyperlinks

def HyperlinkTextDestination(name):
    return E.HyperlinkTextDestination(
        Self="HyperlinkTextDestination/"+name,
        Name=name
        )

@match(transform, "elem.tag=='{%(pub)s}anchor_start'" % pubxml.NS)
def anchor_start(elem, **params):
    # if the anchor has a "Bookmark" attribute
    if elem.get('bkmk') is not None:
        params['Bookmarks'].append(
            Bookmark(elem.get('bkmk'), elem.get('name')))
    return [
        '\n\t',
        CharacterStyleRange(
            HyperlinkTextDestination(elem.get('name')),
            '\n\t', 
            **params
            ),
        '\n\t',
        TextContentCSR(elem.tail, **params)
    ]

@match(transform, "elem.tag=='{%(pub)s}anchor_end'" % pubxml.NS)
def anchor_end(elem, **params):
    return [
        '\n\t',
        CharacterStyleRange(
            HyperlinkTextDestination(elem.get('name')+'_end'),
            '\n\t',
            **params
            ),
        '\n\t',
        TextContentCSR(elem.tail, **params)
    ]

def hyperlink_destination(source_id, anchor=None, url=None, **params):
    if url is None:
        if anchor:
            dest = "HyperlinkTextDestination/" + anchor
            destkey = None
        else:
            return ''
    elif anchor and type(url)==str and os.path.splitext(url)[1].lower()=='.indd':
        dest = "HyperlinkTextDestination/" + anchor
        destkey = None
        icmls = glob(os.path.dirname(params['xml'].fn)+"/*.icml")   # look for destination id in icml files
        for icml in icmls:
            anchors = XML(icml, pubxml.config).root.xpath("//HyperlinkTextDestination[@Name='%s']" % anchor)
            if len(anchors) > 0 and anchors[0].get('DestinationUniqueKey'):
                destkey = anchors[0].get('DestinationUniqueKey')
                break
    else:
        dest = "HyperlinkURLDestination/" + urllib.parse.quote(url)
        destkey = None
        if anchor is not None:
            dest += '#' + anchor

    hid = random_id(8)
    h = E.Hyperlink({'Self': hid, 
                    'Source': source_id, 
                    'Name': "%s_%s" % (dest.replace('HyperlinkTextDestination/',''), hid,)},
            E.Properties(E.Destination({'type':'object'}, dest))
        ); h.tail = '\n'    

    if destkey:
        h.set('DestinationUniqueKey', destkey)

    return h

def HyperlinkTextSource(source_id, text, elems, **params):
    return \
        E.HyperlinkTextSource({'Self': source_id},
            '\n\t',
            TextContentCSR(text, **params),
            '\n\t',
            transform(elems, **params))

@match(transform, "elem.tag=='{%(pub)s}hyperlink'" % pubxml.NS)
def hyperlink_source(elem, **params):
    source_id = random_id(8)
    params['Hyperlinks'].append(
        hyperlink_destination(source_id, 
            anchor=elem.get('anchor'), url=elem.get('filename'), **params))
    return [
        '\n\t',
        HyperlinkTextSource(source_id, elem.text, list(elem), **params),
        '\n\t',
        TextContentCSR(elem.tail, **params)
    ]

@match(transform, "elem.tag=='{%(pub)s}pageref'" % pubxml.NS)
def pageref(elem, **params):
    crossref_id = random_id(8)
    params['Hyperlinks'].append(hyperlink_destination(crossref_id, anchor=elem.get('anchor'), **params))
    e = E.CrossReferenceSource(
            {'Self': crossref_id, 
            'AppliedFormat': 'PageNumberCrossReferenceFormat'},
            E.Content('**UPDATE CROSS-REFERENCE**'),
        )
    if elem.getparent().tag=='{%(html)s}char' % pubxml.NS:
        r = ['\n\t\t', e, '\n\t', E.Content(elem.tail or '')]
    else:
        r = ['\n\t', CharacterStyleRange(e, '\n\t', E.Content(elem.tail or ''), '\n\t', **params)]
    return r

@match(transform, "elem.tag=='{%(pub)s}textref'" % pubxml.NS)
def textref(elem, **params):
    crossref_id = random_id(8)
    params['Hyperlinks'].append(hyperlink_destination(crossref_id, anchor=elem.get('anchor'), **params))
    e = E.CrossReferenceSource(
            {'Self': crossref_id, 
            'AppliedFormat': 'ParagraphTextCrossReferenceFormat'},
            E.Content('**UPDATE CROSS-REFERENCE**'),
        )
    if elem.getparent().tag=='{%(html)s}char' % pubxml.NS:
        r = ['\n\t\t', e, '\n\t', E.Content(elem.tail or '')]
    else:
        r = ['\n\t', CharacterStyleRange(e, '\n\t', E.Content(elem.tail or ''), '\n\t', **params)]
    return r

# == Indexes == 

@match(transform, "elem.tag=='{%(pub)s}xe'" % pubxml.NS)
def xe(elem, **params):
    args = json.dumps(dict(**elem.attrib))
    return [
        '\n\t',
        CharacterStyleRange(
            Note("""{{xe}}%s{{/xe}}""" % args),
            '\n\t',
            **params
            ),
        '\n\t',
        TextContentCSR(elem.tail, **params)
    ]

@match(transform, "elem.tag=='{%(pub)s}index'" % pubxml.NS)
def index(elem, **params):
    args = json.dumps(dict(**elem.attrib))
    return [
        '\n\t',
        CharacterStyleRange(
            Note("{{index}}%s{{/index}}" % args),
            '\n\t',
            **params
            )
    ]

# == Other Inline Elements == 

@match(transform, "elem.tag=='{%(pub)s}image'" % pubxml.NS)
def image(elem, **params):
    return [
        '\n\t\t',
        Note(ElemToCode(elem)),
        TextContentCSR(elem.tail, **params)
    ]

@match(transform, "elem.tag=='{%(pub)s}timestamp'" % pubxml.NS)
def timestamp(elem, **params):
    e = E.TextVariableInstance(
            Self=random_id(6),
            Name="Timestamp",
            ResultText=elem.text or '',
            AssociatedTextVariable="TimestampTextVariable")
    e.tail = '\n\t\t'
    if elem.getparent().tag=='{%(html)s}char' % pubxml.NS:
        r = ['\n\t\t', e, '\n\t', E.Content(elem.tail or '')]
    else:
        r = ['\n\t', CharacterStyleRange(e, '\n\t', E.Content(elem.tail or ''), '\n\t', **params)]
    return r

@match(transform, "elem.tag=='{%(pub)s}tab'" % pubxml.NS)
def tab(elem, **params):
    if elem.get('align')=='right':
        e = E.Content(etree.PIBase('ACE 8'))
    else:
        e = E.Content('\t')
    if elem.getparent().tag=='{%(html)s}char' % pubxml.NS:
        r = ['\n\t\t', e, '\n\t', E.Content(elem.tail or '')]
    else:
        r = ['\n\t', CharacterStyleRange(e, '\n\t', E.Content(elem.tail or ''), '\n\t', **params)]
    return r

@match(transform, """elem.tag=='{%(pub)s}page_break'""" % pubxml.NS)
def page_break(elem, **params): 
    "break_type: 'Next', 'Odd', 'Even'"
    break_type = params.get('break_type') or 'Next'
    return [
        E.ParagraphStyleRange(
            {'AppliedParagraphStyle': 'ParagraphStyle/Force%sPage' % break_type},
            '\n\t',
            CharacterStyleRange(
                E.Br(),
                '\n\t',
                **params
                ),
            '\n'
            ),
        '\n'
    ]

@match(transform, """elem.tag=='{%(html)s}br'""" % pubxml.NS)
def line_break(elem, **params):
    return [
        '\n\t\t',
        E.Content('\u2028',     # line break character
            elem.tail or ''),
    ]

# OTHER

@match(transform, """elem.tag in ['{%(opf)s}metadata', '{%(pub)s}docvars']""" % pubxml.NS)
def omissions(elem, **params):
    return transform.omit(elem, **params)

@match(transform, "True")
def default(elem, **params):
    return [transform.copy(elem, **params)]
