
import os, re, traceback
import glob
from lxml import etree
from time import time

from bl.dict import Dict
from bl.string import String
from bl.text import Text
from bxml.xml import XML
import pubxml

class ICML(XML):
    "model for working with ICML files (also idPkg:Story xml)"
    ROOT_TAG = "Document"
    POINTS_PER_EM = 12
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
        import pubxml.converters.icml_document
        from .document import Document
        x = self.transform(pubxml.converters.icml_document.transformer, 
                            fn=fn or os.path.splitext(self.fn)[0]+'.xml',
                            DocClass=Document,
                            **params)
        return x

    def resources(self, path=None):
        """return a list of files representing the resources in the document"""
        return []

    def metadata(self):
        """return an opf:metadata element with the metadata in the document"""
        # nothing for now
        return etree.Element("{%(pub)s}metadata" % pubxml.NS)

    def stylesheet(self, fn=None, points_per_em=None):
        """create a CSS stylesheet, using the style definitions in the ICML file."""

        from bl.file import File
        from bg.models.styles import Styles

        if points_per_em is None: points_per_em = POINTS_PER_EM

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

            styles[selector] = self.style_block(style, points_per_em=points_per_em)
            # print(selector, styles[selector])

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

    def style_block(self, elem, points_per_em=POINTS_PER_EM):
        "query style elem and return a style definition block"
        s = self.style_attributes(elem, points_per_em=points_per_em)

        # inheritance -- unpack, more reliable than using @extend
        based_on = elem.find('Properties/BasedOn')
        if based_on is not None:
            based_on_styles = elem.xpath("//%s[@Self='%s']" % (elem.tag, based_on.text))
            if len(based_on_styles) > 0:
                # recursive -- each style can override its base style, which is correct inheritance
                bs = self.style_block(based_on_styles[0], points_per_em=points_per_em)
                for k in bs.keys():
                    if k not in s.keys():
                        s[k] = bs[k]

        return s

    def include_mixin(self, style, mixin):
        if style.get('@include') is None:
            style['@include'] = ''
        style['@include'] += ' ' + mixin

    def style_attributes(self, elem, points_per_em=POINTS_PER_EM):
        """query style elem for attributes and return a CSS style definition block.
        """
        s = Dict()

        # color
        if elem.get('FillColor') is not None:
            color = elem.get('FillColor').split('/')[-1]
            if len(color.split(' '))==3:
                r,g,b = [c.split('=')[-1] for c in color.split(' ')]
                s['color:'] = 'rgb(%s,%s,%s)' % (r,g,b)
            elif color=='Black':
                s['color:'] = 'rgb(0,0,0)'
            elif color=='Paper':
                s['color:'] = 'rgb(255,255,255)'
            # print(color, '=', s.get('color:') or 'not converted')

        # direction -- can't be included in epub
        # if elem.get('CharacterDirection') == 'LeftToRightDirection':
        #     s['direction:'] = 'ltr'
        # elif elem.get('CharacterDirection') == 'RightToLeftDirection':
        #     s['direction:'] = 'rtl'

        # font-size
        if elem.get('PointSize') is not None:
            s['font-size:'] = "%.01fem" % round(float(elem.get('PointSize'))/points_per_em, 2)

        # font-family
        if elem.find('Properties/AppliedFont') is not None:
            s['font-family:'] = '"%s"' % elem.find('Properties/AppliedFont').text

        # font-style and font-weight
        fs = elem.get('FontStyle')
        if fs is not None:
            fs = fs.lower()
            if 'bold' in fs or 'black' in fs or 'heavy' in fs:
                s['font-weight:'] = 'bold'
            if 'italic' in fs or 'oblique' in fs:
                s['font-style:'] = 'italic'

        # font-variant
        fv = []
        if elem.get('Capitalization')=='SmallCaps':
            fv.append('small-caps')
        if len(fv) > 0: 
            s['font-variant:'] = ' '.join(fv)

        # hyphens
        # if elem.get('Hyphenation') == 'false':
        #     s['hyphens:'] = 'none'
        #     s['-webkit-hyphens:'] = 'none'

        # letter-spacing
        if elem.get('DesiredLetterSpacing') is not None:
            n = int(elem.get('DesiredLetterSpacing'))
            if n != 0:
                s['letter-spacing:'] = "%d%%" % n

        # margin-left
        if elem.get('LeftIndent') is not None:
            leftindent = float(elem.get('LeftIndent') or 0)/points_per_em
            textindent = float(elem.get('FirstLineIndent') or 0)/points_per_em
            if textindent < 0:  # hanging indent
                val = "%.01fem" % round(leftindent - textindent, 2)
            else:               # regular indent
                val = "%.01fem" % round(leftindent, 2)
            s['margin-left:'] = val

        # margin-right
        if elem.get('RightIndent') is not None:
            val = "%.01fem" % round(float(elem.get('RightIndent'))/points_per_em, 2)
            s['margin-right:'] = val

        # margin-top
        if elem.get('SpaceBefore') is not None:
            val = "%.01fem" % round(float(elem.get('SpaceBefore'))/points_per_em, 2)
            s['margin-top:'] = val

        # margin-bottom
        if elem.get('SpaceAfter') is not None:
            val = "%.01fem" % round(float(elem.get('SpaceAfter'))/points_per_em, 2)
            s['margin-bottom:'] = val

        # text-indent
        if elem.get('FirstLineIndent') is not None:
            indent = float(elem.get('FirstLineIndent'))/points_per_em
            val = "%.01fem" % round(indent, 2)
            s['text-indent:'] = val

        # page-break-before
        if elem.get('StartParagraph') in ['NextColumn', 'NextFrame', 'NextPage']:
            s['page-break-before:'] = 'always'
        elif elem.get('StartParagraph') == 'NextOddPage':
            s['page-break-before:'] = 'right'
        elif elem.get('StartParagraph') == 'NextEvenPage':
            s['page-break-before:'] = 'left'
        elif elem.get('KeepWithPrevious') not in [None, 'false']:
            s['page-break-before:'] = 'avoid'

        # page-break-after
        if elem.get('KeepWithNext') not in [None, 'false']:
            s['page-break-after:'] = 'avoid'

        # text-align
        elem.get('Justification')
        if elem.get('Justification') in ['LeftAlign', 'ToBindingSide']:
            s['text-align:'] = 'left'
        elif elem.get('Justification') == 'CenterAlign':
            s['text-align:'] = 'center'
        elif elem.get('Justification') in ['RightAlign', 'AwayFromBindingSide']:
            s['text-align:'] = 'right'
        elif elem.get('Justification') in ['LeftJustified', 'RightJustified', 'CenterJustified', 'FullyJustified']:
            s['text-align:'] = 'justify'

        # text-decoration (underline, strikethrough)
        td = []
        if elem.get('StrikeThru') == 'true':
            td.append('line-through')
        if elem.get('Underline') == 'true':
            td.append('underline')
        if len(td) > 0:
            s['text-decoration:'] = ' '.join(td)

        # text-transform
        if elem.get('Capitalization')=='AllCaps':
            s['text-transform:'] = 'uppercase'

        # vertical-align
        if elem.get('Position') in ['Superscript', 'OTSuperscript']:
            s['vertical-align:'] = 'top'
            s['font-size:'] = '70%'
        elif elem.get('Position') in ['Subscript', 'OTSubscript']:
            s['vertical-align:'] = 'bottom'
            s['font-size:'] = '70%'
        elif elem.get('CharacterAlignment') in ['AlignBaseline', 'AlignEmBottom', 'AlignICFBottom']:
            s['vertical-align:'] = 'text-bottom'
        elif elem.get('CharacterAlignment') in ['AlignEmCenter']:
            s['vertical-align:'] = 'middle'
        elif elem.get('CharacterAlignment') in ['AlignEmTop', 'AlignICFTop']:
            s['vertical-align:'] = 'text-top'

        # word-spacing
        if elem.get('DesiredWordSpacing') is not None:
            n = int(float(elem.get('DesiredWordSpacing'))) - 100
            if n != 0:
                s['word-spacing:'] = "%d%%" % n

        return s

