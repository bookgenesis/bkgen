# XT stylesheet to transform Word docx to pub:document

import logging
import os
from copy import deepcopy

from bl.url import URL
from bxml.builder import Builder
from bxml.xt import XT
from lxml import etree

from bkgen import NS
from bkgen.document import Document

from ._converter import Converter

log = logging.getLogger(__name__)
B = Builder(default=NS.html, **NS)
transformer = XT()
transformer_XSLT = etree.XSLT(etree.parse(os.path.splitext(__file__)[0] + ".xsl"))


class DocBookDocument(Converter):
    def convert(self, docx, fn=None, **params):
        return docx.transform(transformer, fn=fn, XMLClass=Document, **params)


@transformer.match("True")
def document(elem, **params):
    root = deepcopy(elem)
    root = transformer_XSLT(root).getroot()
    docroot = B.pub.document(B._.body("\n", root, "\n"))
    for e in docroot.xpath("//*[@href or @src]"):
        if e.get("href") is not None:
            e.set("href", str(URL(e.get("href"))))
        if e.get("src") is not None:
            e.set("src", str(URL(e.get("src"))))
    for img in docroot.xpath("//html:img[@height]", namespaces=NS):
        img.set(
            "style", "height:%s;%s" % (img.attrib.pop("height"), img.get("style") or "")
        )
    return [docroot]
