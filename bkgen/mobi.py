
import os, logging, re, subprocess
from bl.dict import Dict
from bl.url import URL
from bl.text import Text
from bf.image import Image
from bf.css import CSS
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
        return os.path.join(
            os.path.dirname(os.path.abspath(mobi_path)), 
            (mobi_name or (os.path.basename(mobi_path.rstrip(os.path.sep))))+ext)

    def build(self, build_path, metadata, mobi_name=None, manifest=None, spine_items=None, cover_src=None, lang='en',
                nav_toc=None, nav_landmarks=None, nav_page_list=None, before_compile=None, progress=None, 
                nav_href='nav.html', nav_title="Navigation"):
        """build MOBI (Kindle ebook) output of the given project"""
        
        from .epub import EPUB
        if mobi_name is None: 
            mobi_name = EPUB.epub_name_from_path(build_path)
        mobifn = self.mobi_fn(build_path, mobi_name=mobi_name)
        if nav_landmarks is None:
            nav_landmarks = EPUB.nav_landmarks({'href':nav_href, 'title':'Table of Contents', 'epub_type':'toc'})
        result = EPUB(**self).build(build_path, metadata, lang=lang, progress=progress,
                    epub_name=mobi_name, spine_items=spine_items, cover_src=cover_src, cover_html=False,
                    nav_toc=nav_toc, nav_landmarks=nav_landmarks, nav_page_list=nav_page_list, 
                    nav_href=nav_href, nav_title=nav_title, show_nav=True, zip=False)
        opffn = EPUB.get_opf_fn(build_path)
        self.strip_header_elements(build_path, opffn)
        
        # # == MOBI 7 adjustments (for Amazon.com page previewer, primarily) ==
        # self.move_anchors_before_paragraphs(build_path, opffn)
        # self.direct_styles(opffn)
        # self.size_images(opffn)
        # self.list_style_type_none_divs(opffn)

        # .mobi doesn't support "display: none;" so we have to remove that from the CSS, 
        # and remove those elements from the interior.
        self.remove_display_none(opffn)

        # .mobi doesn't support CSS ::before or ::after
        self.remove_css_before_after(opffn)

        if before_compile is not None:
            before_compile(build_path)

        if progress is not None: progress.report()

        self.compile_mobi(build_path, opffn, mobifn=mobifn)
        result.update(fn=mobifn, log=mobifn+'.kindlegen.txt', format='mobi')
        if progress is not None: progress.report()
        return result

    @classmethod
    def move_anchors_before_paragraphs(C, build_path, opffn):
        """In Kindle ebooks, link targets **NO LONGER** need to be moved before the containing paragraph so that the 
        paragraph formatting can be displayed properly."""
        opf = XML(fn=opffn)
        n = 0
        for item in opf.root.xpath("opf:manifest/opf:item[contains(@media-type, 'html')]", namespaces=C.NS):
            x = XML(fn=os.path.join(build_path, str(URL(item.get('href')))))
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
            h = HTML(fn=os.path.join(build_path, str(URL(item.get('href')))))
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
            x = XML(os.path.join(os.path.dirname(opffn), str(URL(item.get('href')))))
            for img in x.root.xpath("//html:img[@width or @height or @style]", namespaces=self.NS):
                srcfn = os.path.join(os.path.dirname(x.fn), str(URL(img.get('src'))))
                if os.path.splitext(srcfn)[-1] in ['.svg']: continue
                w, h = [int(i) for i in Image(fn=srcfn).identify(format="%w,%h").split(',')]
                width, height = w, h
                styles = {k:v for k,v in [s.strip().split(':') for s in (img.get('style') or '').split(';') if s.strip()!='']}
                log.debug(img.attrib)
                log.debug(styles)
                if img.get('width') is not None:
                    width = int(re.sub(r'\D', '', img.attrib.pop('width')))     # treat as pixels
                    if img.get('height') is None:
                        height = int(h * (width/w))
                elif styles.get('width') is not None:
                    vv = [i for i in re.split(r'([a-z%]+)', styles.get('width')) if i != '']
                    if len(vv)==2:
                        width, unit = vv
                        if unit in CSS.units.keys():
                            width = int((float(width) * CSS.units[unit]).asUnit(CSS.px) / CSS.px)
                            height = int(height * width / w)
                            styles.pop('width')
                if img.get('height') is not None:
                    height = int(re.sub(r'\D', '', img.attrib.pop('height')))   # treat as pixels
                    if img.get('width') is None:
                        width = int(w * (height/h))
                elif styles.get('height') is not None:
                    vv = [i for i in re.split(r'([a-z%]+)', styles.get('height')) if i != '']
                    if len(vv)==2:
                        height, unit = vv
                        if unit in CSS.units.keys():
                            height = int((float(height) * CSS.units[unit]).asUnit(CSS.px) / CSS.px)
                            width = int(width * height / h)
                            styles.pop('height')
                log.debug("%d x %d\t%d x %d" % (w,h,width,height))
                if (width > 0 and width < w) and (height > 0 and height < h):
                    Image(fn=srcfn).convert(outfn=srcfn, resize="%dx%d>" % (width, height), sharpen="1")
                    log.debug("%dx%d\t%dx%d\t%s" % (w, h, width, height, os.path.relpath(srcfn, os.path.dirname(opffn))))
                img.set('style', ';'.join('%s:%s' % (k,v) for k,v in styles.items()))
            x.write(canonicalized=False)

    def direct_styles(self, opffn):
        """create direct styles for stylesheet elements that some Kindle readers don't support:
        * floats: Kindle iOS
        """
        opf = XML(fn=opffn)
        for item in [item for item in opf.root.xpath(
            "//opf:manifest/opf:item[not(@properties='nav') and @media-type='text/html']", namespaces=self.NS
        )]:
            h = HTML(fn=os.path.join(os.path.dirname(opffn), str(URL(item.get('href')))))
            log.debug(h.fn)
            css = CSS.merge_stylesheets(*[
                os.path.join(h.path, ss.get('href'))
                for ss in h.xpath(h.root, "html:head/html:link[@rel='stylesheet' and @type='text/css']")])
            for sel, style in [[sel, style] for sel,style in css.styles.items() if sel[0]!='@']:
                # floats
                if style.get('float:') in ['left', 'right']:
                    xpath = '//' + CSS.selector_to_xpath(sel, xmlns={'html':h.NS.html})
                    log.debug("%s %r" % (sel, style))
                    log.debug(xpath)
                    for elem in h.xpath(h.root, xpath):
                        styles = {k:v for k,v in [s.strip().split(':') for s in (elem.get('style') or '').split(';') if s.strip()!='']}
                        if 'float' not in styles.keys():
                            styles['float'] = style.get('float:')
                        elem.set('style', ';'.join('%s:%s' % (k,v) for k,v in styles.items())+';')
                        log.debug(elem.attrib)
            h.write()

    def list_style_type_none_divs(self, opffn):
        """convert lists with "list-style-type: none" to nested divs."""
        opf = XML(fn=opffn)
        for item in [item for item in opf.root.xpath(
            "//opf:manifest/opf:item[not(@properties='nav') and @media-type='text/html']", namespaces=self.NS
        )]:
            h = HTML(fn=os.path.join(os.path.dirname(opffn), str(URL(item.get('href')))))
            css = CSS.merge_stylesheets(*[
                os.path.join(h.path, ss.get('href'))
                for ss in h.xpath(h.root, "html:head/html:link[@rel='stylesheet' and @type='text/css']")])
            for sel, style in [
                [sel, style] for sel,style in css.styles.items() 
                if sel[0]!='@' and style.get('list-style-type:')=='none'
            ]:
                xpath = '//' + CSS.selector_to_xpath(sel, xmlns={'html':h.NS.html})
                log.debug("%s %r" % (sel, style))
                log.debug(xpath)
                for elem in h.xpath(h.root, xpath):
                    tag = h.tag_name(elem)
                    elem.tag = "{%(html)s}div" % h.NS
                    elem.set('class', ((elem.get('class') or '') + ' ' + tag).strip())
                    # also convert <li> direct children to <div>
                    for li in h.xpath(elem, "html:li"):
                        tag = h.tag_name(li)
                        li.tag = "{%(html)s}div" % h.NS
                        li.set('class', ((li.get('class') or '') + ' ' + tag).strip())
            h.write()    

    def remove_display_none(self, opffn):
        """Kindle doesn't like too much display:none; so just remove those elements, and remove the instruction from the stylesheets."""
        opf = XML(fn=opffn)
        html_items = [item for item in opf.root.xpath(
            "//opf:manifest/opf:item[not(@properties='nav') and @media-type='text/html']", namespaces=self.NS
        )]
        for item in html_items:
            h = HTML(fn=os.path.join(os.path.dirname(opffn), str(URL(item.get('href')))))
            for link in h.xpath(h.root, "html:head/html:link[@rel='stylesheet' and @type='text/css']"):
                css = CSS(fn=os.path.join(h.path, link.get('href')))
                for sel, style in [
                    [sel, style] for sel,style in css.styles.items() 
                    if sel[0]!='@' and style.get('display:')=='none'
                ]:
                    xpath = '//' + CSS.selector_to_xpath(sel, xmlns={'html':h.NS.html})
                    log.debug("%s %r" % (sel, style))
                    log.debug(xpath)
                    for elem in h.xpath(h.root, xpath):
                        h.remove(elem, leave_tail=True)
                        log.debug(etree.tounicode(elem, with_tail=False))
            h.write()

        for css_item in [item for item in opf.root.xpath(
            "//opf:manifest/opf:item[not(@properties='nav') and @media-type='text/css']", namespaces=self.NS
        )]:
            # do string replace -- easiest
            css = Text(fn=os.path.join(opf.path, css_item.get('href')))
            css.text = css.text.resub("display:\s*none;?\n?", "")
            css.write()

    def remove_css_before_after(self, opffn):
        """remove ::before and ::after selectors from the stylesheets, because they cause problems on the Kindle."""
        opf = XML(fn=opffn)
        for css_item in [item for item in opf.root.xpath(
            "//opf:manifest/opf:item[not(@properties='nav') and @media-type='text/css']", namespaces=self.NS
        )]:
            css = CSS(fn=os.path.join(opf.path, css_item.get('href')))
            for sel in [sel for sel in css.styles.keys() if "::before" in sel or "::after" in sel]:
                css.styles.pop(sel)
            css.write()
        
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