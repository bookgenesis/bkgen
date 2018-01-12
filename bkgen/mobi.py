
import os, logging, re, subprocess
from bl.dict import Dict
from bf.image import Image
from bxml.xml import XML, etree
from bkgen.html import HTML
from bkgen import NS, config

log = logging.getLogger(__name__)

class MOBI(Dict):
    NS = NS

    def __init__(self, **args):
        Dict.__init__(self, **args)

    @classmethod
    def mobi_fn(C, mobi_path, mobi_name=None, ext='.mobi'):
        return os.path.join(os.path.dirname(os.path.abspath(mobi_path)), 
                            (mobi_name or os.path.basename(mobi_path.rstrip(os.path.sep)))+ext)

    def build(self, build_path, metadata, mobi_name=None, manifest=None, spine_items=None, cover_src=None, 
                nav_toc=None, nav_landmarks=None, nav_page_list=None, before_compile=None, before_compile_params={}, 
                nav_href='nav.html', nav_title="Navigation"):
        """build MOBI (Kindle ebook) output of the given project"""
        
        from .epub import EPUB
        if mobi_name is None: mobi_name = EPUB.epub_name_from_path(build_path)
        mobifn = self.mobi_fn(build_path, mobi_name=mobi_name)
        if nav_landmarks is None:
            nav_landmarks = EPUB.nav_landmarks({'href':nav_href, 'title':'Table of Contents', 'epub_type':'toc'})
        result = EPUB(**self).build(build_path, metadata, 
                    epub_name=mobi_name, spine_items=spine_items, cover_src=cover_src, cover_html=False,
                    nav_toc=nav_toc, nav_landmarks=nav_landmarks, nav_page_list=nav_page_list, 
                    nav_href=nav_href, nav_title=nav_title, show_nav=True, zip=False)
        opffn = EPUB.get_opf_fn(build_path)
        self.move_anchors_before_paragraphs(build_path, opffn)
        self.strip_header_elements(build_path, opffn)
        self.size_images(opffn)
        if before_compile is not None:
            before_compile(build_path, **before_compile_params)
        self.compile_mobi(build_path, opffn, mobifn=mobifn)
        result.update(fn=mobifn, log=mobifn+'.kindlegen.txt', format='mobi')
        return result

    @classmethod
    def move_anchors_before_paragraphs(C, build_path, opffn):
        """In Kindle ebooks, link targets need to be moved before the containing paragraph so that the 
        paragraph formatting can be displayed properly."""
        opf = XML(fn=opffn)
        n = 0
        for item in opf.root.xpath("opf:manifest/opf:item[contains(@media-type, 'html')]", namespaces=C.NS):
            x = XML(fn=os.path.join(build_path, item.get('href')))
            anchors = [a for a in 
                    x.root.xpath("//html:a[@id and not(@href)]", namespaces=C.NS)
                    if len(a.getchildren())==0 and a.text in [None, '']]
            for a in anchors:
                pp = a.xpath("ancestor::html:p", namespaces=C.NS)
                if len(pp) > 0:
                    n += 1
                    p = pp[-1]
                    parent = p.getparent()
                    XML.remove(a, leave_tail=True)
                    a.tail = ''
                    parent.insert(parent.index(p), a)
            x.write()

    @classmethod
    def strip_header_elements(C, build_path, opffn):
        """Kindle has trouble with header elements, so we just have to strip them."""
        opf = XML(fn=opffn)
        for item in opf.root.xpath("opf:manifest/opf:item[contains(@media-type, 'html')]", namespaces=C.NS):
            h = HTML(fn=os.path.join(build_path, item.get('href')))
            for header in h.xpath(h.root, "//html:header"):
                HTML.replace_with_contents(header)
            h.write()

    def size_images(self, opffn):
        """resample images to the width / height specified in the img tag, and remove those size attributes"""
        opf = XML(fn=opffn)
        for item in [
                item for item 
                in opf.root.xpath("//opf:manifest/opf:item", namespaces=self.NS) 
                if item.get('href')[-4:].lower()=='html']:
            x = XML(os.path.join(os.path.dirname(opffn), item.get('href')))
            for img in x.root.xpath("//html:img[@width or @height]", namespaces=self.NS):
                srcfn = os.path.join(os.path.dirname(x.fn), img.get('src'))
                if os.path.splitext(srcfn)[-1] in ['.svg']: continue
                w, h = [int(i) for i in Image(fn=srcfn).identify(format="%w,%h").split(',')]
                width, height = w, h
                if img.get('width') is not None:
                    width = int(re.sub(r'\D', '', img.attrib.pop('width')))     # treat as pixels
                    if img.get('height') is None:
                        height = int(h * (width/w))
                if img.get('height') is not None:
                    height = int(re.sub(r'\D', '', img.attrib.pop('height')))   # treat as pixels
                    if img.get('width') is None:
                        width = int(w * (height/h))
                if width != w or height != h:
                    Image(fn=srcfn).convert(outfn=srcfn, resize="%dx%d" % (width, height))
                    log.debug("%dx%d\t%dx%d\t%s" % (w, h, width, height, os.path.relpath(srcfn, os.path.dirname(opffn))))
            x.write(canonicalized=False)

    def compile_mobi(self, build_path, opffn, mobifn=None, config=config):
        """generate .mobi file using kindlegen"""
        if mobifn is None: 
            mobifn = os.path.join(os.path.dirname(build_path), os.path.basename(build_path)+'.mobi')
        logfn = mobifn+'.kindlegen.txt'
        logf = open(logfn, 'wb')
        log.info("mobi: %s" % mobifn)
        cmd = [config.Resources.kindlegen, opffn, '-o', os.path.basename(mobifn), '-verbose']
        subprocess.call(cmd, stdout=logf, stderr=logf)
        logf.close()
        log.info("kindlegen log: %s" % logfn)
        mobi_build_fn = os.path.join(os.path.dirname(opffn), os.path.basename(mobifn))
        if os.path.exists(mobi_build_fn):
            if os.path.exists(mobifn) and mobifn != mobi_build_fn:
                os.remove(mobifn)
            os.rename(mobi_build_fn, mobifn)
        result = dict(fn=mobifn, log=logfn, format='mobi')
        return result

if __name__=='__main__':
    import sys
    from bkgen.epub import EPUB
    logging.basicConfig(**config.Logging)
    for build_path in sys.argv[2:]:
        if sys.argv[1]=='compile':
            opffn = EPUB.get_opf_fn(build_path)
            MOBI().compile_mobi(build_path, opffn)
        else:
            print("unknown command: %s" % sys.argv[1])