# XT stylesheet to transform InDesign AID .xml to pub:document

import os, re, sys, logging
from lxml import etree
from copy import deepcopy

from bxml.xt import XT
from bxml.builder import Builder
from bxml.xslt import XSLT

from bkgen import NS
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)
B = Builder(default=NS.html, **Document.NS)
H = B._
transformer = XT()

class AidDocument(Converter):
    def convert(self, docx, fn=None, **params):
        return docx.transform(transformer, fn=fn, XMLClass=Document, **params)

@transformer.match("True")
def document(elem, **params):
    root = deepcopy(elem)

    body = Document.find(root, "html:body")
    body.text = '\n'

    # body_section = H.section('\n', id='s1'); body_section.tail = '\n'
    # for ch in body.getchildren(): body_section.append(ch)
    # body.insert(0, body_section)

    for e in Document.xpath(root, "//pub:colbreak"): e.tail = '\n'

    for e in Document.xpath(root, "//html:p[html:table]"):
        Document.replace_with_contents(e)

    for e in Document.xpath(root, "//html:p"): 
        e.tail = '\n'
        if e.get('{%(aid)s}pstyle' % NS) is not None:
            e.set('class', e.attrib.pop('{%(aid)s}pstyle' % NS))

    for e in Document.xpath(root, "//html:span|//html:i"): 
        if e.get('{%(aid)s}cstyle' % NS) is not None:
            e.set('class', e.attrib.pop('{%(aid)s}cstyle' % NS))
        if dict(**e.attrib) == {'class':'default'}:
            Document.replace_with_contents(e)

    for e in Document.xpath(root, "//html:img"):
        e.set('src', e.get('href') or e.get('src'))
        if e.get('href_fmt') is not None: e.attrib.pop('href_fmt')
        if e.get('href') is not None: e.attrib.pop('href')

    for e in Document.xpath(root, "//html:td | //html:Cell"):
        e.tag = "{%(html)s}td"%NS
        e.tail = '\n'

        if e.get('{%(aid)s}table'%NS) is not None: e.attrib.pop('{%(aid)s}table'%NS)
        if e.get('aid-table') is not None: e.attrib.pop('aid-table')

        e.set('class', e.get('class') or e.get('{%(aid5)s}cellstyle'%NS) or e.get('aid5-cellstyle') or '')
        if e.get('class')=='': e.attrib.pop('class')
        if e.get('{%(aid5)s}cellstyle'%NS) is not None: e.attrib.pop('{%(aid5)s}cellstyle'%NS)
        if e.get('aid5-cellstyle') is not None: e.attrib.pop('aid5-cellstyle')

        e.set('rowspan', e.get('rowspan') or e.get('{%(aid)s}crows'%NS) or e.get('aid-crows') or '')
        if e.get('rowspan')=='': e.attrib.pop('rowspan')
        if e.get('{%(aid)s}crows'%NS) is not None: e.attrib.pop('{%(aid)s}crows'%NS)
        if e.get('aid-crows') is not None: e.attrib.pop('aid-crows')

        e.set('colspan', e.get('colspan') or e.get('{%(aid)s}ccols'%NS) or e.get('aid-ccols') or '')
        if e.get('colspan')=='': e.attrib.pop('colspan')
        if e.get('{%(aid)s}ccols'%NS) is not None: e.attrib.pop('{%(aid)s}ccols'%NS)
        if e.get('aid-ccols') is not None: e.attrib.pop('aid-ccols')

        e.set('width', e.get('width') or (e.get('{%(aid)s}ccols'%NS) or e.get('aid-ccols') or '') + 'pt')
        if e.get('width')=='pt': e.attrib.pop('width')
        if e.get('{%(aid)s}ccolwidth'%NS) is not None: e.attrib.pop('{%(aid)s}ccolwidth'%NS)
        if e.get('aid-ccolwidth') is not None: e.attrib.pop('aid-ccolwidth')
        
    for e in Document.xpath(root, "//html:table"):
        e.text = '\n'
        e.tail = '\n'

        if e.get('{%(aid)s}table'%NS) is not None: e.attrib.pop('{%(aid)s}table'%NS)
        if e.get('aid-table') is not None: e.attrib.pop('aid-table')

        e.set('class', e.get('class') or e.get('{%(aid5)s}tablestyle') or e.get('aid5-tablestyle') or '')
        if e.get('class')=='': e.attrib.pop('class')
        if e.get('{%(aid5)s}tablestyle'%NS) is not None: e.attrib.pop('{%(aid5)s}tablestyle'%NS)
        if e.get('aid5-tablestyle') is not None: e.attrib.pop('aid5-tablestyle')

        e.set('data-cols', e.get('data-cols') or e.get('{%(aid)s}tcols'%NS) or e.get('aid-tcols') or '')
        if e.get('data-cols')=='': e.attrib.pop('data-cols')
        if e.get('{%(aid)s}tcols'%NS) is not None: e.attrib.pop('{%(aid)s}tcols'%NS)
        if e.get('aid-tcols') is not None: e.attrib.pop('aid-tcols')

        e.set('data-rows', e.get('data-rows') or e.get('{%(aid)s}trows'%NS) or e.get('aid-trows') or '')
        if e.get('data-rows')=='': e.attrib.pop('data-rows')
        if e.get('{%(aid)s}trows'%NS) is not None: e.attrib.pop('{%(aid)s}trows'%NS)
        if e.get('aid-trows') is not None: e.attrib.pop('aid-trows')

    for table in Document.xpath(root, "//html:table"):
        table_cols = int(table.get('data-cols'))
        # table_rows = table.get('data-rows')
        rows = 0
        cols = 0
        tr = H.tr(); tr.tail = '\n'
        for td in Document.xpath(table, "html:td"):
            tr.append(td)
            cols += int(td.get('colspan') or 1)
            if cols >= table_cols:
                rows += 1
                cols = 0
                table.append(tr)
                tr = H.tr(); tr.tail = '\n'
        if tr.getparent() is None and len(tr) > 0:
            table.append(tr)
    
    return [ root ]

