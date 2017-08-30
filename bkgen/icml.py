
import os, re, sys, traceback, logging
import glob
from lxml import etree
from time import time

from bl.dict import Dict
from bl.string import String
from bl.text import Text
from bxml.xml import XML
from bkgen import NS
from bkgen.source import Source

log = logging.getLogger(__name__)

class ICML(XML, Source):
    """model for working with ICML files (also idPkg:Story xml)"""
    ROOT_TAG = "Document"
    PTS_PER_EM = 12
    NS = Dict(**{
            'idPkg': "http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging"
        })

    def documents(self, path=None, **params):
        """return a list of documents containing the content of the document"""
        fn = os.path.join(
                path or os.path.dirname(os.path.abspath(self.fn)),
                os.path.basename(os.path.splitext(self.fn)[0]+'.xml'))
        return [self.document(fn=fn, **params)]

    def document(self, fn=None, **params):
        """produce and return XML output from this ICML document.
        fn = the output filename; default os.path.splitext(ICML.fn)[0] + '.xml'
        """
        import bkgen.converters.icml_document
        from .document import Document
        x = self.transform(bkgen.converters.icml_document.transformer, 
                fn=fn or self.clean_filename(os.path.splitext(self.fn)[0]+'.xml'), 
                DocClass=Document,**params)
        return x

    def metadata(self):
        """return an opf:metadata element with the metadata in the document"""
        # nothing for now
        return etree.Element("{%(pub)s}metadata" % bkgen.NS)

    def stylesheet(self, fn=None, pts_per_em=None):
        """create a CSS stylesheet, using the style definitions in the ICML file."""

        from bl.file import File
        from bf.styles import Styles

        pts_per_em = pts_per_em or self.PTS_PER_EM
        styles = Styles()
        for style in self.root.xpath("//CharacterStyle | //ParagraphStyle"):
            clsname = self.classname(style.get('Name'))
            if style.tag == 'CharacterStyle':
                if clsname == 'No-character-style':
                    selector = 'a, span'
                else:
                    selector = 'a.' + clsname + ', span.' + clsname
            else:
                if clsname == 'No-paragraph-style':
                    selector = 'p'
                else:
                    selector = 'p.' + clsname
                    if len(self.root.xpath(
                            "//ParagraphStyleRange[@AppliedParagraphStyle='%s' and .//Table]" 
                            % style.get('Self'))) > 0:
                        selector += ', div.' + clsname

            styles[selector] = self.style_block(style, pts_per_em=pts_per_em)

        ss = Text(fn=fn or os.path.splitext(self.fn)[0]+'.css', text=Styles.render(styles))
        return ss

    @classmethod
    def classname(C, stylename):
        """convert an Indesign style name into an HTML class name"""
        name = stylename.replace('$ID/','').strip('/').replace('[','').replace(']','').replace(' ', '-')
        name = String(name.split(':')[-1]).camelsplit().strip()
        name = re.sub('[^0-9A-Za-z_\-]+', '-', name)
        if re.search("^\d" ,name[0:1]) is not None:
            name = '_' + name
        return name

    # query the style element for each supported attribute and build 
    # its value based on what is there. Work by CSS attributes rather
    # than by ICML properties -- treat the style element as data to query

    def style_block(self, elem, pts_per_em=None):
        """query style elem and return a style definition block
        """
        pts_per_em = pts_per_em or self.PTS_PER_EM
        style = Dict()

        # inheritance via recursion
        based_on = elem.find('Properties/BasedOn')
        if based_on is not None:
            based_on_elem = XML.find(elem, "//*[@Self='%s']" % based_on.text)
            if based_on_elem is not None:
                style = self.style_block(based_on_elem, pts_per_em=pts_per_em)

        # local definitions will override base definitions
        style.update(**self.style_attribute(elem, pts_per_em=pts_per_em))

        return style

    def include_mixin(self, style, mixin):
        if style.get('@include') is None:
            style['@include'] = ''
        style['@include'] += ' ' + mixin

    @classmethod
    def lang_attribute(Class, elem):
        import pycountry
        if elem.get('AppliedLanguage') is not None:
            lang = pycountry.languages.lookup(elem.get(key).split('/')[-1].split(':')[0])
            if lang is not None:
                return lang.alpha_2
            else:
                log.warn('AppliedLanguage=%r' % elem.get('AppliedLanguage'))

    @classmethod
    def style_attribute(Class, elem, pts_per_em=None):
        """query style elem for attributes and return a CSS style definition block.
        """
        log.debug(elem.attrib)
        pts_per_em = pts_per_em or Class.PTS_PER_EM
        style = Dict()

        # capitalization
        cap = elem.get('Capitalization')
        if cap in ['SmallCaps', 'CapToSmallCap']:
            style['font-variant:'] = 'small-caps'
        elif cap=='AllCaps':
            style['text-transform:'] = 'uppercase'
        elif cap=='Normal':
            style['text-transform:'] = 'none'
            style['font-variant:'] = 'normal'
        elif cap is not None:
            log.warn('Capitalization=%r' % cap)

        # color
        if elem.get('FillColor') is not None:
            color = elem.get('FillColor').split('/')[-1]
            cmyk = re.match(r'^C=(\d+) M=(\d+) Y=(\d+) K=(\d+)$', color)
            rgb = re.match(r'^R=(\d+) G=(\d+) B=(\d+)$', color)
            if cmyk is not None:
                style['color:'] = ('cmyk(%s%%, %s%%, %s%%, %s%%)' 
                    % (cmyk.group(1), cmyk.group(2), cmyk.group(3), cmyk.group(4)))
            elif rgb is not None:
                style['color:'] = ('rgb(%s%%, %s%%, %s%%, %s%%)' 
                    % (rgb.group(1), rgb.group(2), rgb.group(3)))
            elif color=='Black':
                style['color:'] = 'rgb(0,0,0)'
            elif color=='Paper':
                style['color:'] = 'rgb(255,255,255)'
            else:
                style['color:'] = '"%s"' % color
                log.warn("color=%r" % color)

        # direction
        direction = elem.get('CharacterDirection')
        if direction is not None:
            if direction == 'LeftToRightDirection':
                style['direction:'] = 'ltr'
            elif direction == 'RightToLeftDirection':
                style['direction:'] = 'rtl'
            elif direction != 'DefaultDirection':
                log.warn("CharacterDirection=%r" % direction)

        # font-family
        if elem.find('Properties/AppliedFont') is not None:
            style['font-family:'] = '"%s"' % elem.find('Properties/AppliedFont').text

        # font-size
        if elem.get('PointSize') is not None:
            style['font-size:'] = "%.02frem" % (float(elem.get('PointSize'))/pts_per_em, )

        # font-style and font-weight
        fs = elem.get('FontStyle')
        if fs is not None:
            if 'Italic' in fs or 'Oblique' in fs:
                style['font-style:'] = 'italic'

            if 'semibold' in fs.lower():
                style['font-weight:'] = '600'
            elif 'Bold' in fs:
                style['font-weight:'] = 'bold'
            elif 'Heavy' in fs:
                style['font-weight:'] = '800'
            elif 'Black' in fs:
                style['font-weight:'] = '900'
            elif 'Medium' in fs or 'Regular' in fs:
                style['font-weight:'] = 'normal'
            elif 'Extralight' in fs or 'Thin' in fs:
                style['font-weight:'] = '100'
            elif 'Light' in fs:
                style['font-weight:'] = '200'
            elif re.match('^\d+$', fs):
                style['font-weight'] = fs
            elif fs in ['Italic', 'Oblique']:
                style['font-weight:'] = 'normal'
                style['font-style:'] = 'italic'
            else:
                log.warn("FontStyle=%r" % fs)
            
        # hyphens
        if elem.get('Hyphenation') == 'false':
            style['hyphens:'] = 'none'
            style['-webkit-hyphens:'] = 'none'

        # letter-spacing
        if elem.get('DesiredLetterSpacing') is not None:
            n = int(elem.get('DesiredLetterSpacing'))
            if n != 0:
                style['letter-spacing:'] = "%d%%" % n

        # margin-left
        if elem.get('LeftIndent') is not None:
            style['margin-left:'] = "%.02frem" % (float(elem.get('LeftIndent'))/pts_per_em, )

        # margin-right
        if elem.get('RightIndent') is not None:
            style['margin-right:'] = "%.02frem" % (float(elem.get('RightIndent'))/pts_per_em, )

        # margin-top
        if elem.get('SpaceBefore') is not None:
            style['margin-top:'] = "%.02frem" % (float(elem.get('SpaceBefore'))/pts_per_em, )

        # margin-bottom
        if elem.get('SpaceAfter') is not None:
            style['margin-bottom:'] = "%.02frem" % (float(elem.get('SpaceAfter'))/pts_per_em, )

        # text-indent
        if elem.get('FirstLineIndent') is not None:
            style['text-indent:'] = "%.02frem" % (float(elem.get('FirstLineIndent'))/pts_per_em, )

        # page-break-before
        if elem.get('StartParagraph') in ['NextColumn', 'NextFrame', 'NextPage']:
            style['page-break-before:'] = 'always'
        elif elem.get('StartParagraph') == 'NextOddPage':
            style['page-break-before:'] = 'right'
        elif elem.get('StartParagraph') == 'NextEvenPage':
            style['page-break-before:'] = 'left'
        elif elem.get('KeepWithPrevious') not in [None, 'false']:
            style['page-break-before:'] = 'avoid'

        # page-break-after
        if elem.get('KeepWithNext') not in [None, 'false']:
            style['page-break-after:'] = 'avoid'

        # text-align
        elem.get('Justification')
        if elem.get('Justification') in ['LeftAlign', 'ToBindingSide']:
            style['text-align:'] = 'left'
        elif elem.get('Justification') == 'CenterAlign':
            style['text-align:'] = 'center'
        elif elem.get('Justification') in ['RightAlign', 'AwayFromBindingSide']:
            style['text-align:'] = 'right'
        elif elem.get('Justification') in ['LeftJustified', 'RightJustified', 'CenterJustified', 'FullyJustified']:
            style['text-align:'] = 'justify'

        # text-decoration (underline, strikethrough)
        td = []
        if elem.get('StrikeThru') == 'true':
            td.append('line-through')
        if elem.get('Underline') == 'true':
            td.append('underline')
        if len(td) > 0:
            style['text-decoration:'] = ' '.join(td)

        # vertical-align
        position, alignment = elem.get('Position'), elem.get('CharacterAlignment')
        if position in ['Superscript', 'OTSuperscript']:
            style['vertical-align:'] = 'super'
        elif position in ['Subscript', 'OTSubscript']:
            style['vertical-align:'] = 'sub'
        elif position=='Normal':
            style['vertical-align:'] = 'baseline'
        elif alignment in ['AlignBaseline', 'AlignEmBottom', 'AlignICFBottom']:
            style['vertical-align:'] = 'text-bottom'
        elif alignment in ['AlignEmCenter']:
            style['vertical-align:'] = 'middle'
        elif alignment in ['AlignEmTop', 'AlignICFTop']:
            style['vertical-align:'] = 'text-top'
        elif position is not None or alignment is not None:
            log.warn("Position=%r, CharacterAlignment=%r" % (position, alignment))

        # word-spacing
        if elem.get('DesiredWordSpacing') is not None:
            n = int(float(elem.get('DesiredWordSpacing'))) - 100
            if n != 0:
                style['word-spacing:'] = "%d%%" % n

        log.debug("=> style: %r" % style)
        return style

