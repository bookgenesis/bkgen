"""
The bkgen module
================
The bkgen module itself provides several objects when imported:

* **bkgen.config**: The module configuration (a bl.config.Config object, which is a nested Dict) containing several sections that are stored in the main __config__.ini file.
* **bkgen.NS**: Namespaces that are used in book production.
* **bkgen.mimetypes**: The python mimetypes module, with the included mimetypes customized for common book content types.
"""

import os, mimetypes
from bl.dict import Dict
from bl.config import Config

PATH = os.path.dirname(os.path.abspath(__file__))
config = Config(fn=os.path.join(PATH, '__config__.ini'))
resources_path = os.path.join(PATH, 'resources')
config.Resources = Dict(
    path=resources_path,
    publishingxml=os.path.join(resources_path, 'publishing-xml'),
    schemas=os.path.join(resources_path, 'publishing-xml', 'schemas'),
    epubcheck=os.path.join(resources_path, 'epubcheck-4.0.2/epubcheck.jar'),
    kindlegen=os.path.join(resources_path, 'KindleGen_Mac_i386_v2_9/kindlegen'),
    mimetypes=os.path.join(resources_path, 'mime.types'),
)

mimetypes.init(files=[config.Resources.mimetypes])

NS = Dict(
    pub="http://publishingxml.org/ns",
    html="http://www.w3.org/1999/xhtml",
    dc="http://purl.org/dc/elements/1.1/",                                   # Dublin Core & friends
    dcterms="http://purl.org/dc/terms/", 
    dcmitype="http://purl.org/dc/dcmitype/", 
    xsi="http://www.w3.org/2001/XMLSchema-instance",                         # XML & friends
    xml="http://www.w3.org/XML/1998/namespace",
    opf="http://www.idpf.org/2007/opf",                                      # Digital Publishing
    container="urn:oasis:names:tc:opendocument:xmlns:container", 
    epub="http://www.idpf.org/2007/ops",
    ncx="http://www.daisy.org/z3986/2005/ncx/",
    cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties",    # Microsoft
)

