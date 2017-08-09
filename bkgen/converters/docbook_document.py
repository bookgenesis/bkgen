# XT stylesheet to transform Word docx to pub:document

import os, re, sys, logging
from lxml import etree
from copy import deepcopy
import urllib.parse

from bl.dict import Dict
from bl.string import String
from bl.url import URL
from bxml.xml import XML
from bxml.xt import XT
from bxml.builder import Builder
from bxml.xslt import XSLT

from bkgen import NS
from bkgen.converters import Converter
from bkgen.document import Document

log = logging.getLogger(__name__)
B = Builder(default=NS.html, **NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocBookDocument(Converter):
    def convert(self, docx, fn=None, **params):
        return docx.transform(transformer, fn=fn, XMLClass=Document, **params)

@transformer.match("True")
def document(elem, **params):
    root = deepcopy(elem)
    root = transformer_XSLT(root).getroot()
    docroot = B.pub.document(B._.body('\n', root, '\n'))
    for e in docroot.xpath("//*[@href or @src]"):
        if e.get('href') is not None: e.set('href', e.get('href').replace('\\','/'))
        if e.get('src') is not None: e.set('src', e.get('src').replace('\\','/'))
    for img in docroot.xpath("//html:img[@height]", namespaces=NS):
        img.set('style', 'height:%s;%s' % (img.attrib.pop('height'), img.get('style') or ''))
    return [ docroot ]

