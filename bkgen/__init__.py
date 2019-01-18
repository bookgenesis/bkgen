import os, sys, mimetypes
from bl.dict import Dict
from bl.config import Config

PATH = os.path.dirname(os.path.abspath(__file__))
PACKAGE_PATH = os.path.dirname(PATH)
config = Config(fn=os.path.join(PATH, '__config__.ini')) 

RESOURCES_PATH = os.path.join(PACKAGE_PATH, 'resources')
config.Resources = Dict(
    path=RESOURCES_PATH,
    publishingxml=os.path.join(RESOURCES_PATH, 'publishing-xml'),
    schemas=os.path.join(RESOURCES_PATH, 'publishing-xml', 'schemas'),
    epubcheck=os.path.join(RESOURCES_PATH, 'epubcheck-4.0.2/epubcheck.jar'),
    kindlegen=os.path.join(RESOURCES_PATH,
        ('darwin' in sys.platform and 'KindleGen_Mac_i386_v2_9/kindlegen')
        or ('linux' in sys.platform and 'kindlegen_linux_2.6_i386_v2_9/kindlegen')
        or ('win32' in sys.platform and 'kindlegen_win32_v2_9/kindlegen.exe')
        or None),
    daisyace=os.path.join(PACKAGE_PATH, 'node_modules', '@daisy', 'ace', 'bin', 'ace.js'),
    mimetypes=os.path.join(RESOURCES_PATH, 'mime.types'),
)


mimetypes.init(files=[config.Resources.mimetypes])              

NS = Dict(
    pub="http://publishingxml.org/ns",
    html="http://www.w3.org/1999/xhtml",
    aid="http://ns.adobe.com/AdobeInDesign/4.0/",                                   # InDesign
    aid5="http://ns.adobe.com/AdobeInDesign/5.0/",
    dc="http://purl.org/dc/elements/1.1/",                                          # Dublin Core etc.
    dcterms="http://purl.org/dc/terms/", 
    dcmitype="http://purl.org/dc/dcmitype/", 
    xsi="http://www.w3.org/2001/XMLSchema-instance",                                # XML
    xml="http://www.w3.org/XML/1998/namespace",
    opf="http://www.idpf.org/2007/opf",                                             # EPUB etc.
    container="urn:oasis:names:tc:opendocument:xmlns:container", 
    epub="http://www.idpf.org/2007/ops",
    ncx="http://www.daisy.org/z3986/2005/ncx/",
    cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties",   # Microsoft
    m="http://www.w3.org/1998/Math/MathML",                                         # MathML
    db="http://docbook.org/ns/docbook",                                             # DocBook
)

