
import os
from bl.url import URL
from bxml.xml import XML
from .epub import EPUB

class ADE(EPUB):
    """Adobe Digital Editions (ADE) EPUB file.
    Everything works similarly to EPUB, but if the nav file has a page-list,
    ADE adds a page-map file from the nav file.
    """

    @classmethod
    def build(C, epub_path, metadata, pagemap_href="page-map.xml", zip_epub=True, **kwargs):
        """build the ADE EPUB file"""
        # first use the EPUB.build() procedure
        epubfn = EPUB.build(epub_path, metadata, zip_epub=False, **kwargs)
        opffn = C.get_opf_fn(epub_path)

        # add the page map if it exists
        navfn = C.get_nav_fn(epub_path)
        if navfn is not None and opffn is not None:
            # make the page map file
            pagemap_fn = C.make_page_map_file(epub_path, navfn, pagemap_href=pagemap_href)
            if pagemap_fn is not None:
                # add page map to the opf manifest and spine
                opf = XML(fn=opffn)
                pagemap_id =  C.href_to_id(pagemap_href)
                manifest = opf.root.find("{%(opf)s}manifest" % C.NS)
                manifest.append(
                    C.OPF.item({
                        'href': pagemap_href,
                        'id': pagemap_id,
                        'media-type': "application/oebps-page-map+xml"
                        }))
                spine = opf.root.find("{%(opf)s}spine" % C.NS)
                spine.set('page-map', pagemap_id)
                opf.write()

        # now zip the epub
        return C.zip(epub_path, 
                    epubfn=epubfn,
                    opf_fn=opffn, 
                )   

    @classmethod
    def make_page_map_file(C, epub_path, nav_fn, pagemap_href='page-map.xml'):
        nav = XML(fn=nav_fn)
        page_list = nav.root.find(".//{%(html)s}nav[@{%(epub)s}type='page-list']" % C.NS)
        if page_list is not None:
            pagemap = XML(
                fn=os.path.join(epub_path, pagemap_href),
                root=C.OPF('page-map'))
            for a in page_list.xpath(".//html:a[@href]", namespaces=C.NS):
                pagemap.root.append(
                    C.OPF.page(
                        name=a.text, 
                        href=str(URL(a.get('href')))))
            pagemap.write()
            return pagemap.fn