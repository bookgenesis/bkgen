# XT .icml to pub:document

import logging
import os
import re
import tempfile
import urllib.parse

from bl.dict import Dict
from bl.file import File
from bl.id import random_id
from bl.string import String
from bl.url import URL
from bxml.builder import Builder
from bxml.xml import XML
from bxml.xt import XT
from lxml import etree

import bkgen
from bkgen.document import Document
from bkgen.icml import ICML

from ._converter import Converter

log = logging.getLogger(__name__)


NS = Document.NS
NS.update(**{k: bkgen.NS[k] for k in bkgen.NS if "aid" in k})
B = Builder(default=NS.html, **NS)
transformer = XT()


class IcmlDocument(Converter):
    def convert(self, icml, **params):
        return icml.transform(transformer, XMLClass=Document, **params)


# == Document ==
@transformer.match("elem.tag in ['Document', '{%(idPkg)s}Story']" % ICML.NS)
def TheDocument(elem, **params):
    if params.get("document_path") is None:
        params["document_path"] = os.path.dirname(params.get("fn"))
    if params.get("fns") is not None:
        # load all the documents in params['fns']
        params["documents"] = [XML(fn=fn) for fn in params["fns"]]
    params["footnotes"] = []

    elem = pre_process(elem, **params)
    root = B.pub.document(
        "\n\t", B.html.body("\n", transformer(elem.getchildren(), **params))
    )
    root = post_process(root, **params)
    return [root]


# == Story ==
@transformer.match("elem.tag=='Story'")
def Story(elem, **params):
    section = B.html.section(
        {"class": "Story", "id": make_element_id(elem, **params)},
        "\n",
        transformer(elem.getchildren(), **params),
    )
    ptitle = Document.find(section, "html:p[contains(@class,'Title')]")
    if ptitle is not None:
        title = (
            String(etree.tounicode(ptitle, method="text", with_tail=False))
            .resub(r"<[^>]+>", r"")
            .resub(r"\s+", " ")
            .strip()
        )
        log.debug(title)
        section.set("title", title)
    section = process_para_breaks(section)
    section = nest_span_hyperlinks(section)
    section = split_sections(section)
    return [section]


# == ParagraphStyleRange ==
@transformer.match("elem.tag=='ParagraphStyleRange'")
def ParagraphStyleRange(elem, **params):
    # create the p class attribute
    styles = params.get("styles")
    ps = (
        elem.get("AppliedParagraphStyle")
        .replace("ParagraphStyle/", "")
        .replace("%3a", ":")
        .replace(": ", ":")
    )
    p_class = ICML.classname(ps)
    if "p_class" not in params:
        params["p_class"] = p_class
    p = B.html.p({"class": p_class}, "", transformer(elem.getchildren(), **params))
    list_type = (
        elem.get("BulletsAndNumberingListType")
        or styles is not None
        and styles.get(elem.get("AppliedParagraphStyle")) is not None
        and styles.get(elem.get("AppliedParagraphStyle")).get(
            "BulletsAndNumberingListType"
        )
        or None
    )
    if list_type not in [None, "NoList"]:
        p.set("BulletsAndNumberingListType", list_type)
    result = [p, "\n"]
    # if there is a pub:section_start in the paragraph, move it out.
    section_start = XML.find(p, ".//pub:section_start", namespaces=NS)
    if section_start is not None:
        XML.remove(section_start, leave_tail=True)
        result = [section_start, "\n"] + result
    return result


# == CharacterStyleRange ==
@transformer.match("elem.tag=='CharacterStyleRange'")
def CharacterStyleRange(elem, **params):
    if elem.find("Table") is not None:
        return transformer(elem.getchildren(), **params)
    else:
        cs = (
            elem.get("AppliedCharacterStyle")
            .replace("CharacterStyle/", "")
            .replace("%3a", ":")
            .replace(": ", ":")
        )
        attribs = character_attribs(elem)
        span_class = ICML.classname(cs)
        if "span_class" not in params:
            params["span_class"] = span_class
        if span_class not in ["", None, "Default-Paragraph-Font", "No-character-style"]:
            attribs["class"] = span_class
        if elem.get("AppliedConditions") is not None:
            conditions = [
                c.replace("Condition/", "").replace("%20", "_")
                for c in elem.get("AppliedConditions").split(" ")
            ]
            # space-separated list
            attribs["{%(pub)s}cond" % NS] = " ".join(conditions)

        result = []

        # use regular spans, and MathML embedded in MathTools MathZones
        if bool(elem.get("MathToolsML")) is True:
            # MathML
            mml_text = elem.get("MathToolsML").replace("&quot;", '"').strip()
            mml_text = re.sub("&lt;((?!&[lg]t;).*?)&gt;", r"<\1>", mml_text)
            log.debug(mml_text)
            mml = etree.fromstring(mml_text)

            span = B.html.span(attribs, mml)
            result += [span]

            # add preceeding and trailing whitespace that might be embedded in the
            # MathML, because we're going to trim the math
            mml_string = etree.tounicode(mml, method="text", with_tail=False)
            if re.search(r"^\s+", mml_string) is not None:
                result = [" "] + result
            if re.search(r"\s+$", mml_string) is not None:
                result += [" "]

        elif bool(elem.get("MTMathZone")) is False:
            # regular span
            span = B.html.span(attribs, transformer(elem.getchildren(), **params))
            result += [span]

        # else MTMathZone but not MathToolsML, so skip

        return result


def character_attribs(elem):
    """return common character attributes on elem"""
    attrib = Dict()
    style = ICML.style_attribute(elem)
    if style.keys() != []:
        attrib.style = "; ".join(["%s%s" % (k, style[k]) for k in style.keys()])
    lang = ICML.lang_attribute(elem)
    if lang is not None:
        attrib.lang = lang
    return attrib


@transformer.match("elem.tag=='HiddenText'")
def HiddenText(elem, **params):
    return transformer(
        elem.getchildren(), **{k: params[k] for k in params if "_style" not in k}
    )


# == Note ==
@transformer.match("elem.tag=='Note'")
def Note(elem, **params):
    namespaces = 'xmlns:pub="http://publishingxml.org/ns" xmlns:epub="http://www.idpf.org/2007/ops"'
    texts = XML.xpath(elem, ".//Content/text()")
    content = "".join(texts)
    if content[0:1] == "<" and content[-1:] == ">":
        # add namespaces: pub, epub
        content = re.sub(r"^<(\w+)\b(.*)$", r"<\1 %s\2" % namespaces, content)
        e = etree.fromstring(content)
        return [e]
    else:
        return []
    # return transformer(tagged_content, **params)


# == Content ==
@transformer.match("elem.tag=='Content'")
def Content(elem, **params):
    # create a temporary container -- will be stripped later.
    t = B.pub.t(elem.text or "", transformer(elem.getchildren(), **params))
    # \t characters to <pub:tab/>
    content = etree.fromstring(
        etree.tounicode(t, with_tail=False)
        .replace("\t", "<pub:tab xmlns:pub='%(pub)s'/>" % NS)
        .encode("utf-8")
    )
    content.tail = ""
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
        k: params[k] for k in params.keys() if k not in ["p_class", "span_class"]
    }
    if elem not in params["footnotes"]:
        params["footnotes"].append(elem)
    fn_id = str(params["footnotes"].index(elem) + 1)
    return [
        B.pub.footnote(
            # id is the index + 1 of this footnote in document footnotes
            {"id": "fn" + fn_id},
            transformer(elem.getchildren(), **fn_params),
        )
    ]


# == Table ==
@transformer.match("elem.tag=='Table'")
def Table(elem, **params):
    attrib = {}
    if XML.find(elem, "@AppliedTableStyle") is not None:
        attrib["class"] = ICML.classname(
            elem.get("AppliedTableStyle")
            .split("/")[-1]
            .replace("%3a", ":")
            .replace(": ", ":")
        )
    table = B.html.table(attrib, "\n\t", transformer(elem.getchildren(), **params))
    return [table, "\n"]


@transformer.match("elem.tag=='Row'")
def Row(elem, **params):
    tr = B.html.tr("\n\t\t")
    tail = ":" + elem.get("Name")
    len_tail = len(tail)
    for cell in [
        cell
        for cell in elem.xpath("../Cell[contains(@Name, ':%s')]" % elem.get("Name"))
        if cell.get("Name")[-len_tail:] == tail
    ]:
        tr.append(Cell(cell, **params)[0])
    return [tr, "\n\t"]


def Cell(elem, **params):
    cell_params = {
        k: params[k] for k in params.keys() if k not in ["p_class", "span_class"]
    }
    td = B.html.td("\n", transformer(elem.getchildren(), **cell_params))
    if elem.get("AppliedCellStyle") is not None:
        td.set("class", ICML.classname(elem.get("AppliedCellStyle")))
    col_span = elem.get("ColumnSpan")
    if int(col_span) > 1:
        td.set("colspan", col_span)
    return [td, "\n\t\t"]


# == HyperlinkTextDestination ==
@transformer.match("elem.tag=='HyperlinkTextDestination'")
def HyperlinkTextDestination(elem, **params):
    result = []
    attrib = {"id": make_element_id(elem, **params)}

    # If the anchor defines a bookmark, create a section_start
    bookmark_xpath = (
        "//Bookmark[@Destination='HyperlinkTextDestination/%s']" % elem.get("Name")
    )
    bookmark = find_in_documents_or_sources(elem, bookmark_xpath, **params)
    if bookmark is not None:
        attrib.update(title=bookmark_title(bookmark["element"]))
        section_start = B.pub.section_start(
            **{k: v for k, v in attrib.items() if v is not None}
        )
        result += [section_start]

    # otherwise, insert an anchor
    else:
        anchor = B.pub.anchor(**{k: v for k, v in attrib.items() if v is not None})
        result += [anchor]
    return result


@transformer.match("elem.tag=='ParagraphDestination'")
def ParagraphDestination(elem, **params):
    log.debug("%r %r" % (elem.tag, elem.attrib))
    anchor = B.pub.anchor(id=make_element_id(elem, **params))
    result = [anchor]
    return result


# == HyperlinkTextSource  or CrossReferenceSource ==
@transformer.match("elem.tag in ['HyperlinkTextSource', 'CrossReferenceSource']")
def HyperlinkTextOrCrossReferenceSource(elem, **params):
    hyperlink = B.html.a(
        {"id": make_element_id(elem, **params)},
        transformer(elem.getchildren(), **params),
    )
    cc = hyperlink.getchildren()
    result = None
    if len(cc) == 1 and cc[0].tag == "{%(pub)s}cref" % NS:
        for k in hyperlink.attrib.keys():
            cc[0].set(k, hyperlink.get(k))
        result = cc
    else:
        find_xpath = "//Hyperlink[@Source='%(Self)s']" % elem.attrib
        found_hyperlink = find_in_documents_or_sources(elem, find_xpath, **params)
        if found_hyperlink is None:
            log.warn("No hyperlink found for %s=%r" % (XML.tag_name(elem), elem))
        else:
            hyperlink.attrib.update(
                hyperlink_href(found_hyperlink["element"], **params)
            )
            result = [hyperlink]

    return result


def hyperlink_href(hyperlink_elem, source=None, **params):
    attribs = {}
    if hyperlink_elem.get("DestinationUniqueKey") is not None:
        find_xpath = (
            "//*[contains(name(), 'Destination') and @DestinationUniqueKey='%s']"
            % hyperlink_elem.get("DestinationUniqueKey")
        )
        found = find_in_documents_or_sources(hyperlink_elem, find_xpath, **params)
        if found is not None:
            attribs["idref"] = make_element_id(found["element"], fn=found["filename"])
            attribs["filename"] = found["filename"]
        else:
            attribs["idref"] = make_element_id(hyperlink_elem)
    destination = hyperlink_elem.find("Properties/Destination")
    if destination is not None:
        if "HyperlinkTextDestination/" in destination.text:
            find_xpath = "//HyperlinkTextDestination[@Self='%s']" % destination.text
            found = find_in_documents_or_sources(hyperlink_elem, find_xpath, **params)
            if found is not None:
                attribs["idref"] = make_element_id(
                    found["element"], fn=found["filename"]
                )
                attribs["filename"] = found["filename"]
        elif "HyperlinkURLDestination/" in destination.text:
            find_xpath = "//HyperlinkURLDestination[@Self='%s']" % destination.text
            found = find_in_documents_or_sources(hyperlink_elem, find_xpath, **params)
            if found is not None:
                attribs["idref"] = make_element_id(
                    found["element"], fn=found["filename"]
                )
                attribs["filename"] = found["element"].get("DestinationURL")
        elif destination.get("type") == "list":
            # first list item is filename
            attribs["filename"] = (
                os.path.splitext(XML.find(destination, "ListItem/text()"))[0] + ".xml"
            )
            # rewrite the idref to include the filename component
            attribs["idref"] = (
                make_identifier(
                    os.path.splitext(os.path.basename(attribs["filename"]))[0]
                )
                + "_"
                + attribs["idref"]
            )
    return {
        "href": f"{attribs.get('filename') or ''}#{attribs.get('idref') or ''}".rstrip(
            "#"
        )
    }


def find_in_documents_or_sources(elem, xpath, **params):
    """find the given xpath target in the current document or the accompanying documents and sources
    params['documents'] = ICML file objects
    params['sources'] = IDML file objects
    """
    target_elem = XML.find(elem, xpath, namespaces=Document.NS)
    if target_elem is not None:
        result = {
            "element": target_elem,
            "filename": os.path.splitext(os.path.basename(params["fn"]))[0] + ".xml",
        }
        return result
    for doc in (params.get("documents") or []) + (params.get("sources") or []):
        target_elem = (doc.root and XML.find(doc.root, xpath)) or (
            doc.designmap and XML.find(doc.designmap.root, xpath)
        )
        if target_elem is not None:
            result = {
                "element": target_elem,
                "filename": os.path.splitext(os.path.basename(doc.fn))[0] + ".xml",
            }
            return result


def make_element_id(elem, fn=None, **params):
    """make sure the anchor id will be valid. Use this for all anchors, section ids, etc."""
    if fn is not None:
        id = make_identifier(os.path.splitext(os.path.basename(fn))[0]) + "_"
    else:
        id = ""
    if elem.get("DestinationUniqueKey") is not None:
        id += f"dest_{elem.get('DestinationUniqueKey')}"
    elif elem.get("Self") is not None:
        id += String(elem.get("Self").split("/")[-1]).identifier().resub(r"[_\W]+", "_")
    elif elem.get("Name") is not None:
        id += String(elem.get("Name").split("/")[-1]).identifier().resub(r"[_\W]+", "_")
    else:
        id += String(etree.tounicode(elem).strip()).digest(alg="md5")
    return id


def make_identifier(string):
    return String(os.path.splitext(string)[0]).identifier()


def bookmark_title(bookmark):
    title = XML.find(bookmark, "Properties/Label/KeyValuePair[@Label]/@Value")
    if title is not None:
        title = str(title).strip()
    else:
        title = bookmark.get("Name").replace("_", " ").strip()
    return title


# == TextVariableInstance ==
@transformer.match("elem.tag=='TextVariableInstance'")
def TextVariableInstance(elem, **params):
    found = find_in_documents_or_sources(
        elem, "//TextVariable[@Self='%s']" % elem.get("AssociatedTextVariable")
    )
    if found is not None:
        text_variable = found["element"]
        variable_type = text_variable.get("VariableType")
        if variable_type == "XrefPageNumberType":  # page references
            return [B.pub.cref(elem.get("ResultText"))]
        elif variable_type == "ModificationDateType":  # modification date
            return [
                B.pub.modified(
                    elem.get("ResultText") or "",
                    idformat=text_variable.find("DateVariablePreference").get("Format"),
                )
            ]
    return [B.pub.textvariable(elem.get("ResultText"), **elem.attrib)]


# == Rectangle ==
@transformer.match("elem.tag=='Rectangle'")
def Rectangle(elem, **params):
    return transformer(elem.getchildren(), **params)


@transformer.match(
    "elem.tag in ['Image', 'PDF', 'EPS', 'PICT', 'WMF', 'ImportedPage', 'Graphic']"
)
def Graphic(elem, **params):
    attribs = {
        "src": graphic_src(elem, **params),
        "class": XML.find(elem, "(ancestor::*/@AppliedObjectStyle)[1]").split("/")[-1],
    }
    attribs["style"] = (
        (attribs.get("style") or "")
        + " "
        + "; ".join(["%s:%s" % (k, v) for k, v in graphic_geometry(elem).items()])
        + ";"
    ).strip()
    attribs = {k: v for k, v in attribs.items() if v is not None}
    log.debug(f"img {attribs}")
    return [B.html.img(**attribs)]


def graphic_src(elem, **params):
    link = elem.find("Link")
    if link is not None and link.get("LinkResourceURI") is not None:
        url = URL(link.get("LinkResourceURI"))
        log.debug("Graphic Link URL = %r %r" % (str(url), url.items()))
        relpath = File(url.path).relpath(
            os.path.dirname(params.get("srcfn") or params.get("fn") or "")
        )
        if relpath != url.path:
            src = relpath
        elif url.scheme == "file":
            src = url.path
        else:
            src = str(url)
        return src


def graphic_geometry(elem):
    """use the GraphicBounds, ActualPpi, and EffectivePpi of the graphic to determine display size"""
    # All InDesign geometry is in points, 72 pt = 1 inch
    # @ItemTransform: transformation to page coordinates. what a clever but horrible way to store it
    # -- I can't actually unpack this matrix, not invertible (see idml_specification pp. 98–99).
    # We can use it where there is no rotation or skew. Otherwise, use ActualPpi vs EffectivePpi.

    geometry = {}

    # internal coordinates of the graphic itself
    graphic_bounds = [float(i) for i in XML.xpath(elem, "Properties/GraphicBounds/@*")]
    size_x = graphic_bounds[2] - graphic_bounds[0]
    size_y = graphic_bounds[3] - graphic_bounds[1]

    # If there is no rotation or skew, we can use the ItemTransform matrix
    item_transform = [
        float(i) for i in (XML.find(elem, "@ItemTransform") or "").split(" ")
    ]
    if len(item_transform) == 6 and item_transform[1:3] == [0.0, 0.0]:
        resize_x = item_transform[0]
        resize_y = item_transform[3]
        geometry["width"] = "%.2fpt" % (size_x * resize_x)
        # geometry['height'] = "%.2fpt" % (size_y * resize_y)

    # otherwise, if there are ActualPpi and EffectivePpi, use that to get the width & height
    elif elem.get("ActualPpi") is not None and elem.get("EffectivePpi") is not None:
        # the resize factor is @ActualPpi divided by @EffectivePpi
        actual_ppi = [float(i) for i in XML.find(elem, "@ActualPpi").split(" ")]
        effective_ppi = [float(i) for i in XML.find(elem, "@EffectivePpi").split(" ")]
        resize_x = actual_ppi[0] / effective_ppi[0]
        resize_y = actual_ppi[1] / effective_ppi[1]
        geometry["width"] = "%.2fpt" % (size_x * resize_x)
        # geometry['height'] = "%.2fpt" % (size_y * resize_y)

    return geometry


# == XML Element ==
@transformer.match("elem.tag=='XMLElement'")
def XMLElement(elem, **params):
    tag = urllib.parse.unquote(elem.get("MarkupTag").split("/")[-1])
    if ":" in tag:
        ns, tag = tag.split(":")
    else:
        ns = "_"
    e = B[ns](tag, transformer(elem.getchildren(), **params))
    for attr in elem.xpath("XMLAttribute"):
        if "xmlns:" not in attr.get("Name"):
            attr_name = urllib.parse.unquote(attr.get("Name"))
            if ":" in attr_name:
                ns, attr_name = attr_name.split(":")
                attr_name = "{%s}%s" % (NS[ns], attr_name)
            e.set(attr_name, attr.get("Value"))
    return [e]


# == TextFrame ==
@transformer.match("elem.tag=='TextFrame'")
def TextFrame(elem, **params):
    div = B.html.div(B.pub.include(idref=elem.get("ParentStory")))
    div.set("class", (elem.get("AppliedObjectStyle") or "").split("/")[-1])
    return [div]


# == Processing Instructions ==
@transformer.match("type(elem)==etree._ProcessingInstruction")
def ProcessingInstruction(elem, **params):
    pitext = etree.tounicode(elem).strip("<?>")
    if pitext[:5] == "ACE 4":
        r = [B.pub.footnote_ref()]
    elif pitext[:5] in ["ACE 7", "ACE 8"]:
        r = ["\t"]
    else:
        r = []
    return r + [elem.tail]


# == Changes ==
@transformer.match("elem.tag=='Change'")
def Change(elem, **params):
    """
    Deal with redlining. For now, just provide the results.
    Later, we'll support the HTML <ins> and <del> tags.
    """
    # attrib = dict(
    #     datetime=elem.get('Date'),
    #     title="user=%r" % elem.get('UserName').replace('$ID/',''),
    # )
    if elem.get("ChangeType") in ["InsertedText", "MovedText"]:
        # res = B.html('ins', attrib, transformer(elem.getchildren(), **params))
        return transformer(elem.getchildren(), **params)
    elif elem.get("ChangeType") == "DeletedText":
        # res = B.html('del', attrib, transformer(elem.getchildren(), **params))
        pass
    else:
        log.warn("Invalid ChangeType: %r" % elem.get("ChangeType"))


# == omitted/ignored ==
omitted = [
    "Bookmark",
    "Cell",
    "Color",
    "ColorGroup",
    "Column",
    "CompositeFont",
    "CrossReferenceFormat",
    "DocumentUser",
    "FontFamily",
    "FrameFittingOption",
    "Group",
    "Hyperlink",
    "HyperlinkURLDestination",
    "InCopyExportOption",
    "Ink",
    "MetadataPacketPreference",
    "NumberingList",
    "ObjectExportOption",
    "Oval",
    "Properties",
    "RootCellStyleGroup",
    "RootCharacterStyleGroup",
    "RootObjectStyleGroup",
    "RootParagraphStyleGroup",
    "RootTableStyleGroup",
    "StandaloneDocumentPreference",
    "StoryPreference",
    "StrokeStyle",
    "Swatch",
    "TextWrapPreference",
    "TinDocumentDataObject",
    "TransparencyDefaultContainerObject",
    "Condition",
    "TextVariable",
    "KinsokuTable",
    "MojikumiTable",
    "XMLAttribute",
    "AnchoredObjectSetting",
    "Polygon",
]


@transformer.match("elem.tag in %s" % str(omitted))
def omissions(elem, **params):
    return transformer.omit(elem, keep_tail=False, **params)


# == default ==
@transformer.match("True")
def default(elem, **params):
    return [transformer.copy(elem, **params)]


def pre_process(root, **params):
    # root = embed_textframes(root)
    root = convert_tabs(root)
    return root


def post_process(root, **params):
    root = convert_line_page_breaks(root)
    root = remove_empty_spans(root)
    root = process_t_codes(root)
    root = process_endnotes(root)
    root = hyperlinks_inside_paras(root)
    root = unpack_nested_paras(root)
    root = anchors_shift_paras(root)
    root = anchors_outside_hyperlinks(root)
    root = anchors_inside_paras(root)
    root = fix_endnote_refs(root)
    if params.get("preserve_paragraphs") is not True:
        root = remove_empty_paras(root)
    if params.get("convert_lists") is True:
        root = convert_lists(root)
    else:
        for p in Document.xpath(root, "//html:p[@BulletsAndNumberingListType]"):
            p.attrib.pop("BulletsAndNumberingListType")
    root = remove_container_sections(root)
    root = unnest_p_divs(root)
    root = unnest_tables_from_p(root)
    for section in root.xpath("//html:section", namespaces=NS):
        chs = section.getchildren()
        if len(chs) == 1 and chs[0].tag == "{%(pub)s}include" % bkgen.NS:
            Document.replace_with_contents(section)
        else:
            section.tail = "\n"
    for incl in root.xpath("//html:p/pub:include", namespaces=NS):
        XML.unnest(incl)
    root = remove_empty_p(root)
    root = p_tails(root)
    return root


def embed_textframes(root):
    for textframe in root.xpath("//TextFrame[@ParentStory]"):
        textframe_stories = root.xpath(
            "//Story[@Self='%s']" % textframe.get("ParentStory")
        )
        if len(textframe_stories) < 1:
            continue
        textframe_story = textframe_stories[0]
        parent = textframe.getparent()
        while parent.tag in ["ParagraphStyleRange", "CharacterStyleRange"]:
            XML.unnest(textframe)
            parent = textframe.getparent()
        for e in textframe_story.getchildren():
            parent.insert(parent.index(textframe), e)
        parent.remove(textframe)
        textframe_story.getparent().remove(textframe_story)
    return root


def convert_tabs(root):
    txt = etree.tounicode(root)
    txt = txt.replace("<?ACE 8?>", "<pub:tab align='right' xmlns:pub='%(pub)s'/>" % NS)
    txt = txt.replace("<?ACE 7?>", "")  # align "here" tab
    with tempfile.TemporaryDirectory() as td:
        tfn = td + "/doc.xml"
        with open(tfn, "wb") as tf:
            tf.write(txt.encode("utf-8"))
        d = etree.parse(tfn).getroot()
    return d


def remove_empty_spans(root):
    for span in root.xpath("//html:span", namespaces=NS):
        if span.attrib.keys() == [] or XML.is_empty(span, ignore_whitespace=True):
            XML.replace_with_contents(span)
    return root


def process_t_codes(root):
    for t in root.xpath("//pub:t", namespaces=NS):
        XML.replace_with_contents(t)
    return root


def convert_line_page_breaks(root):
    txt = etree.tounicode(root)
    txt = txt.replace("\u2028", "<br/>")  # forced line break
    txt = txt.replace("\u200b", "")  # discretionary line break / zero-width space
    txt = txt.replace("<page ", "<pub:page xmlns:pub='%(pub)s' " % NS)  # page codes
    return etree.fromstring(txt.encode("utf-8"))


def process_endnotes(root):
    # enclose endnotes that are tagged with endnote_start
    for e in root.xpath("//html:endnote_start", namespaces=NS):
        e.tag = "{%(pub)s}endnote" % NS
        nxt = e.getnext()
        while nxt is not None and nxt.tag != "{%(pub)s}endnote_start" % NS:
            e.append(nxt)
            nxt = e.getnext()

    # for now, just strip off the endnote characteristics so that HTML output can be processed
    for endnote in root.xpath("//html:endnote", namespaces=NS):
        endnote.text = endnote.tail = None
        XML.replace_with_contents(endnote)
    for ie in root.xpath("//html:insert_endnotes", namespaces=NS):
        XML.replace_with_contents(ie)
    return root


def hyperlinks_inside_paras(root):
    "hyperlinks that cross paragraph boundaries need to be nested inside the paragraphs"
    for hyperlink in root.xpath("//pub:hyperlink[html:p]", namespaces=NS):
        XML.interior_nesting(hyperlink, "html:p", namespaces=NS)
    return root


def unpack_nested_paras(root):
    """HiddenText (conditional text) often results in nested paras, they need to be unpacked"""
    for p in root.xpath("//html:p/html:p", namespaces=NS):
        XML.unnest(p)
    return root


def sections_outside_paras(root):
    for section in root.xpath("//html:p/html:section", namespaces=NS):
        XML.unnest(section)
    return root


def remove_empty_paras(root):
    """empty paras are meaningless and removed."""
    for p in root.xpath(".//html:p", namespaces=NS):
        XML.remove_if_empty(p, leave_tail=False, ignore_whitespace=True)
    return root


def convert_lists(root):
    """paragraphs with automatic numbering / bullets are converted to lists"""
    p = XML.find(root, ".//html:p[@BulletsAndNumberingListType]", namespaces=bkgen.NS)
    while p is not None:
        list_type = p.get("BulletsAndNumberingListType")
        if "Numbered" in list_type:
            tag = "ol"
        elif "Bullet" in list_type:
            tag = "ul"
        else:
            p = XML.find(
                p,
                "following::html:p[@BulletsAndNumberingListType]",
                namespaces=bkgen.NS,
            )
            continue
        list_elem = B.html(tag, "\n")
        list_elem.tail = "\n"
        parent = p.getparent()
        parent.insert(parent.index(p), list_elem)
        nxt = list_elem.getnext()
        while (
            nxt is not None
            and nxt.tag == "{%(html)s}p" % bkgen.NS
            and nxt.get("BulletsAndNumberingListType") == list_type
        ):
            list_elem.append(B.html.li(nxt))
            nxt.attrib.pop("BulletsAndNumberingListType")
            nxt = list_elem.getnext()
        p = XML.find(
            list_elem,
            "following::html:p[@BulletsAndNumberingListType]",
            namespaces=bkgen.NS,
        )
    return root


def p_tails(root):
    for p in root.xpath(
        ".//html:p | .//html:table | .//html:div | .//html:section", namespaces=NS
    ):
        p.tail = "\n"
    return root


def anchors_shift_paras(root):
    # a monstrosity
    for p in root.xpath("//html:p", namespaces=NS):
        while (
            len(p.getchildren()) > 0
            and p.text in [None, ""]
            and p.getchildren()[0].tag
            in ["{%(pub)s}anchor" % NS, "{%(pub)s}anchor_end" % NS]
        ):
            a = p.getchildren()[0]
            while (
                a is not None
                and a.tag == "{%(pub)s}anchor" % NS
                and a.tail in [None, ""]
            ):
                a = a.getnext()
            if a is None or a.tag != "{%(pub)s}anchor_end" % NS:
                break
            prevs = p.xpath("preceding::html:p", namespaces=NS)
            if len(prevs) > 0:
                prev = prevs[-1]
                while (
                    prev is not None
                    and len(prev.getchildren()) == 0
                    and prev.text in [None, ""]
                ):
                    prevs = prev.xpath("preceding::html:p", namespaces=NS)
                    if len(prevs) == 0:
                        break
                    prev = prevs[-1]
                if prev is not None:
                    XML.remove(a, leave_tail=True)
                    a.tail = ""
                    prev.append(a)
            else:
                break
        while (
            len(p.getchildren()) > 0
            and p.getchildren()[-1].tag == "{%(pub)s}anchor" % NS
            and p.getchildren()[-1].tail in [None, ""]
        ):
            a = p.getchildren()[-1]
            nexts = p.xpath("following::html:p", namespaces=NS)
            if len(nexts) > 0:
                XML.remove(a, leave_tail=True)
                nexts[0].insert(0, a)
                if nexts[0].text not in [None, ""]:
                    nexts[0].text, a.tail = "", nexts[0].text
            else:
                break
    return root


def anchors_outside_hyperlinks(root):
    "make sure anchors are outside of hyperlinks"
    for a in root.xpath("//pub:anchor[ancestor::pub:hyperlink]", namespaces=NS):
        h = a.xpath("ancestor::pub:hyperlink", namespaces=NS)[0]
        XML.remove(a)
        a.tail = ""
        parent = h.getparent()
        parent.insert(parent.index(h), a)
    for a in root.xpath("//pub:anchor_end[ancestor::pub:hyperlink]", namespaces=NS):
        h = a.xpath("ancestor::pub:hyperlink", namespaces=NS)[0]
        XML.remove(a)
        a.tail = ""
        parent = h.getparent()
        parent.insert(parent.index(h) + 1, a)
    return root


def anchors_inside_paras(root):
    """anchor at the start of the next para, anchor_end at the end of the previous para"""
    for anchor in root.xpath("//pub:anchor[not(ancestor::html:p)]", namespaces=NS):
        paras = anchor.xpath("following::html:p", namespaces=NS)
        if len(paras) > 0:
            para = paras[0]
            XML.remove(anchor, leave_tail=True)
            para.insert(0, anchor)
            anchor.tail, para.text = para.text, ""
    for anchor_end in root.xpath(
        "//pub:anchor_end[not(ancestor::html:p)]", namespaces=NS
    ):
        paras = anchor_end.xpath("preceding::html:p", namespaces=NS)
        if len(paras) > 0:
            para = paras[-1]
            XML.remove(anchor_end, leave_tail=True)
            para.append(anchor_end)
    return root


def fix_endnote_refs(root):
    "make sure endnote references are superscript"
    for hyperlink in root.xpath(
        """
        //pub:hyperlink[
            not(ancestor::html:span) 
            and not(html:span) 
            and contains(@anchor, 'endnote_ref_')
        ]
        """,
        namespaces=NS,
    ):
        span = B.html.span({"class": "_Endnote Reference"})
        span.text, hyperlink.text = hyperlink.text or "", ""
        for ch in hyperlink.getchildren():
            span.append(ch)
        hyperlink.insert(0, span)
    return root


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
    for span in body.xpath("//html:span[pub:hyperlink]", namespaces=NS):
        XML.fragment_nesting(span, "pub:hyperlink", namespaces=NS)
    return body


def split_sections(body):
    """convert pub:section_start tags into html:section elements"""
    sections = XML.xpath(body, ".//pub:section_start", namespaces=NS)
    for section in sections:
        section.tag = "{%(html)s}section" % NS
        section.text = "\n"
        next = section.getnext()
        while next is not None and next.tag != "{%(pub)s}section_start" % NS:
            elem = next
            next = elem.getnext()
            section.append(elem)
    return body


def is_prev_node_br(elem):
    prev = elem.getprevious()
    if prev is not None and prev.tag == "Br":
        return True
    else:
        # TODO: figure out how to do this properly with xpath
        parent = elem.xpath("..")
        if len(parent) > 0:
            prev_parent = parent[0].getprevious()
            if prev_parent is not None:
                p_children = prev_parent.getchildren()
                if len(p_children) > 0:
                    if p_children[-1].tag == "Br":
                        return True
    return False


def remove_container_sections(root):
    """Remove sections that are just containers for other sections"""
    sections = reversed(root.xpath("html:body/html:section", namespaces=NS))
    for section in sections:
        if (
            section.xpath("*") == section.xpath("html:section", namespaces=NS)
            and (section.text or "").strip() == ""
        ):
            XML.replace_with_contents(section)
    return root


def unnest_p_divs(root):
    """unnest <div> from inside <p>"""
    for div in Document.xpath(root, "//html:div[ancestor::html:p]"):
        while Document.find(div, "ancestor::html:p") is not None:
            Document.unnest(div)
        div.text = div.tail = "\n"
    return root


def unnest_tables_from_p(root):
    for table in Document.xpath(root, "//html:p/html:table"):
        Document.unnest(table)
    return root


def remove_empty_p(root):
    for p in root.xpath(
        """
        .//html:*[
            not(ancestor::html:table) 
            and (name()='p' or name()='h1' or name()='h2' or name()='h3' or name()='h4' 
                or name()='h5' or name()='h6' or name()='h7' or name()='h8' or name()='h9')]
    """,
        namespaces=NS,
    ):
        if (p.text is None or p.text.strip() == "") and len(p.getchildren()) == 0:
            XML.remove(p, leave_tail=True)
    return root
