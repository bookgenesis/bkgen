"""convert pub:document and document fragments to (X)HTML"""

import logging
log = logging.getLogger(__name__)

import os
from lxml import etree
from bxml.xt import XT
from bxml.builder import Builder
from bl.file import File
from bxml.xml import XML

from bkgen import NS
from bkgen.converters import Converter
from bkgen.document import Document

B = Builder(**NS)
H = Builder.single(NS.html)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + '.xsl'))

class DocumentAid(Converter):
    def convert(self, document, **params):
        return document.transform(transformer, **params)

# == DEFAULT == 
# do XSLT on the element and return the results
@transformer.match("True")
def default(elem, **params):
    e = get_includes(elem, **params)
    e = transformer_XSLT(e).getroot()
    e = image_hrefs(e, **params)
    return [ e ]

def get_includes(root, **params):
    for incl in root.xpath("//pub:include", namespaces=NS):
        for ch in incl: 
            incl.remove(ch)
        srcfn = os.path.join(os.path.dirname(params['fn']), incl.get('src').split('#')[0])
        assert os.path.exists(srcfn)
        src = XML(fn=srcfn)
        if '#' in incl.get('src'):
            srcid = incl.get('src').split('#')[-1]
            elems = XML.xpath(src.root, "//*[@id='%s']" % srcid)
        else:
            elems = XML.xpath(src.root, "html:body/*", namespaces=NS)
        for elem in elems:
            incl.append(elem)
    return root

def image_hrefs(root, **params):
    for img in root.xpath("//html:img", namespaces=NS):
        img.set('href', 'file://'+os.path.abspath(os.path.join(os.path.dirname(params['fn']), img.get('src'))))
    return root

