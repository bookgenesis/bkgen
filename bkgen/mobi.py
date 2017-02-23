
import os, subprocess
from bl.dict import Dict
from bf.image import Image
from bxml.xml import XML, etree
import bg

class MOBI(Dict):
    NS = bg.NS

    def __init__(self, log=print, **args):
        Dict.__init__(self, log=log, **args)

    @classmethod
    def mobi_fn(C, mobi_path, mobi_name=None, ext='.mobi'):
        return os.path.join(os.path.dirname(os.path.abspath(mobi_path)), 
                            (mobi_name or os.path.basename(mobi_path.rstrip(os.path.sep)))+ext)

    def build(self, build_path, metadata, mobi_name=None, manifest=None, spine_items=None, cover_src=None, 
                nav_toc=None, nav_landmarks=None, nav_page_list=None, 
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
                    nav_href=nav_href, nav_title=nav_title, zip=False)
        self.move_anchors_before_paragraphs(build_path, opffn)
        EPUB.unhide_toc(os.path.join(build_path, nav_href))
        EPUB.append_toc_to_spine(opffn, nav_href)
        self.size_images(opffn)
        self.compile_mobi(build_path, opffn, mobifn=mobifn)
        result.fn=mobifn
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
                w, h = [int(i) for i in Image(fn=srcfn).identify(format="%w,%h").split(',')]
                width, height = w, h
                if img.get('width') is not None:
                    width = int(img.attrib.pop('width'))
                    if img.get('height') is None:
                        height = int(h * (width/w))
                if img.get('height') is not None:
                    height = int(img.attrib.pop('height'))
                    if img.get('width') is None:
                        width = int(w * (height/h))
                if width != w or height != h:
                    Image(fn=srcfn).convert(outfn=srcfn, resize="%dx%d" % (width, height))
                    print("%dx%d\t%dx%d\t%s" % (w, h, width, height, os.path.relpath(srcfn, os.path.dirname(opffn))))
            x.write(canonicalized=False)


    def compile_mobi(self, build_path, opffn, mobifn=None):
        """generate .mobi file using kindlegen"""
        if mobifn is None: 
            mobifn = os.path.join(os.path.dirname(build_path), os.path.basename(build_path)+'.mobi')
        logfn = mobifn+'.kindlegen.txt'
        logf = open(logfn, 'wb')
        print("compiling", mobifn)
        cmd = [bg.config.Resources.kindlegen, opffn, '-o', os.path.basename(mobifn)]
        subprocess.call(cmd, stdout=logf, stderr=logf)
        logf.close()
        mobi_build_fn = os.path.join(os.path.dirname(opffn), os.path.basename(mobifn))
        if os.path.exists(mobi_build_fn):
            if os.path.exists(mobifn) and mobifn != mobi_build_fn:
                os.remove(mobifn)
            os.rename(mobi_build_fn, mobifn)        

