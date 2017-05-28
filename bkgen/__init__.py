"""
bkgen
=====
The bkgen module provides several objects when imported.

bkgen.config
    configuration for bkgen, used throughout the bkgen module 

    bkgen.config.Logging 
        parameters fed to new loggers.

    bkgen.config.Project
        values for project parameters, if different from the defaults.

    bkgen.config.EPUB
        EPUB parameters, such as specs for images

    bkgen.config.Kindle
        Kindle build parameters

    bkgen.config.Resources
        other resources used by bkgen. (These configuration parameters should generally not be changed,
        so they are stored in the module source file.)

bkgen.mimetypes
    The Python mimetypes module, with customized mimetypes as found in the package Resources.

bkgen.NS
    XML namespaces used by the bkgen package. These include:

    =========== =========================================================================   =========================
    label       namespace                                                                   Notes
    =========== =========================================================================   =========================
    html        "http://www.w3.org/1999/xhtml"                                              XHTML Content Documents
    dc          "http://purl.org/dc/elements/1.1/"                                          Metadata
    dcterms     "http://purl.org/dc/terms/"
    dcmitype    "http://purl.org/dc/dcmitype/"
    opf         "http://www.idpf.org/2007/opf"                                              EPUB / Digital Publishing
    container   "urn:oasis:names:tc:opendocument:xmlns:container"
    epub        "http://www.idpf.org/2007/ops"
    pub         "http://publishingxml.org/ns"                                               Publishing XML
    ncx         "http://www.daisy.org/z3986/2005/ncx/"
    xsi         "http://www.w3.org/2001/XMLSchema-instance"                                 Generic XML Namespaces
    xml         "http://www.w3.org/XML/1998/namespace"
    cp          "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"   Microsoft
    =========== =========================================================================   =========================
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
    opf="http://www.idpf.org/2007/opf",                                      #: Digital Publishing
    container="urn:oasis:names:tc:opendocument:xmlns:container", 
    epub="http://www.idpf.org/2007/ops",
    ncx="http://www.daisy.org/z3986/2005/ncx/",
    cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties",    #: Microsoft
)

