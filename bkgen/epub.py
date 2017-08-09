
DEBUG = False

import os, logging, mimetypes, shutil, subprocess, traceback, zipfile
from datetime import datetime
from copy import deepcopy
from lxml import etree
from bl.dict import Dict
from bl.string import String
from bl.rglob import rglob
from bxml.xml import XML
from bl.zip import ZIP
from bl.text import Text
from bl.file import File
from bxml.builder import Builder
from bkgen import NS, config
from bkgen.source import Source

log = logging.getLogger(__name__)
FILENAME = os.path.abspath(__file__)

ALLOWED_DATE_PROPERTIES = [                                     # allowed on dc:date
    'id', 'dir', '{%(xml)s}lang' % NS]
ALLOWED_META_PROPERTIES = [                                     # allowed on opf:meta
    'alternate-script', 'display-seq', 'file-as', 
    'group-position', 'identifier-type', 'meta-auth', 'role']

class EPUB(ZIP, Source):
    NS = NS
    OPF = Builder(**NS).opf
    MEDIATYPES = Dict(**{
        '.ncx': 'application/x-dtbncx+xml',
        '.opf': 'application/oebps-package+xml',
        '.epub': 'application/epub+zip',
        '.xhtml': 'application/xhtml+xml'
    })

    def check(self):
        """use epubcheck to validate the epub"""
        checkfn = self.fn + '.epubcheck.txt'
        checkf = open(checkfn, 'wb')
        cmd = ['java', '-jar', config.Resources.epubcheck, self.fn]
        subprocess.call(cmd, stdout=checkf, stderr=checkf)
        checkf.close()
        log.info("epubcheck log: %s" % checkfn)
        return checkfn

    def write(self, fn=None):
        f = File(fn=self.fn)
        fd = f.read()
        f.write(fn=fn, data=fd)

    def get_opf(self):
        """return the opf as an XML document"""
        container = XML(root=self.zipfile.read('META-INF/container.xml'))
        zf_path = container.find(container.root, "//container:rootfile/@full-path", namespaces=NS)
        opf = XML(
                root=self.zipfile.read(zf_path), 
                fn=os.path.join(self.fn, zf_path))
        return opf

    def documents(self, path=None, opf=None):
        """return a list of pub:document containing the content in the EPUB
        path = the output path for the documents.
        """
        from .html import HTML
        if path is None: path = os.path.dirname(os.path.abspath(self.fn))
        if opf is None: opf = self.get_opf()
        docs = []
        # build docs from the spine so that they're in the correct order
        for itemref in opf.xpath(opf.root, "opf:spine/opf:itemref", namespaces=NS):
            href = opf.find(opf.root, 
                    "opf:manifest/opf:item[@id='%s']/@href" % itemref.get('idref'), 
                    namespaces=NS)
            zf_path = os.path.relpath(os.path.join(os.path.dirname(opf.fn), href), self.fn).replace('\\','/')
            html = HTML(root=self.zipfile.read(zf_path), fn=os.path.join(path, href))
            docpath = os.path.join(path, os.path.dirname(href)).rstrip('/')
            doc = html.document(fn=os.path.join(docpath, os.path.splitext(os.path.basename(html.fn))[0]+'.xml'))
            docs.append(doc)
        return docs

    def images(self):
        return []

    def resources(self, path=None, opf=None):
        """return a list of files containing project resources in the EPUB
        path = the output path for the resources
        """
        if path is None: path = os.path.dirname(os.path.abspath(self.fn))
        if opf is None: opf = self.get_opf()
        res = []
        items = [
            item for item in
            opf.xpath(opf.root, "opf:manifest/opf:item", namespaces=NS)
            if item.get('media-type') not in [
                EPUB.MEDIATYPES[k] for k in EPUB.MEDIATYPES.keys()
                if k in ['.ncx', '.xhtml', '.opf', '.epub']
            ]
        ]
        found_cover = False
        for item in items:
            href = item.get('href')
            zf_path = os.path.relpath(
                os.path.join(
                    os.path.dirname(opf.fn), 
                    href), 
                self.fn).replace('\\','/')
            fn = os.path.join(path, href)
            fd = self.zipfile.read(zf_path)
            f = File(fn=fn, mediatype=item.get('media-type'))
            if 'cover-image' in (item.get('properties') or ''):
                f['class'] = 'cover-digital'
                found_cover = True
            f.write(data=fd)
            res.append(f)

        if found_cover == False:
            # look in the metadata block
            cover_id = opf.find(opf.root, 
                "opf:metadata/opf:meta[@name='cover']/@content", namespaces=NS)
            if cover_id is not None:
                item = opf.find(opf.root, 
                    "opf:manifest/opf:item[@id='%s']" % cover_id, namespaces=NS)
                if item is not None:
                    fn = os.path.join(path, item.get('href'))
                    fns = [f.fn for f in res]
                    if fn in fns:
                        f = res[fns.index(fn)]
                        f['class'] = 'cover-digital'

        return res

    def metadata(self, opf=None):
        """return an opf:metadata element with the metadata in the EPUB"""
        if opf is None: opf = self.get_opf()
        return opf.find(opf.root, "opf:metadata", namespaces=NS)

    @classmethod
    def build(C, output_path, metadata, epub_name=None, manifest=None, spine_items=None, 
                cover_src=None, cover_html=True, nav_toc=None, nav_landmarks=None, 
                nav_page_list=None, nav_href='nav.xhtml', nav_title="Navigation", 
                show_nav=False, before_compile=None, zip=True, check=True):
        """build EPUB file output; returns EPUB object
        
        REQUIRED parameters:
            output_path   = where the build files are to be located
            metadata    = a metadata element to be used in building the EPUB 

        OPTIONAL parameters:
            epub_name   = the base filename for the build; or = output_path basename
            manifest    = the opf:manifest to use; or built from crawling the output_path
            spine_items = a list of dicts that have the following attributes:

                'href'      : REQUIRED relative file path from output_path 
                'idref'     : opf:itemref/@idref (default generated from href)
                'linear'    : opf:itemref/@linear (="yes"|"no", default "yes")
                'properties': opf:itemref/@properties
                'title'     : can be used to populate nav items
                'landmark'  : if given, included in landmarks nav with this landmark epub:type

            cover_src   = the cover image src; or no cover included
            cover_html  = whether to include the cover in the first html document (default True).
            nav_toc     = a toc nav element for the nav; or built from opf:spine_items
            nav_landmarks = a landmarks nav element for the nav; or built
            nav_page_list = a page-list nav element for the nav; or built
            nav_href    = the relative path to use for the nav file (also ncx)
            nav_title   = the title to display on the nav page
            zip_epub    = if True, zip the EPUB after building

        """
        if not os.path.isdir(output_path): 
            os.makedirs(output_path)
        if epub_name is None: 
            epub_name = C.epub_name_from_path(output_path)
        
        opf_metadata = C.opf_package_metadata(metadata, cover_src=cover_src) 

        if cover_src is not None and cover_html==True:
            cover_html_relpath = os.path.relpath(C.make_cover_html(output_path, cover_src), output_path)
            spine_items.insert(0, Dict(href=cover_html_relpath, landmark='cover'))
        else:
            cover_html_relpath = None

        # nav file
        if nav_toc is None:
            nav_toc = C.nav_toc_from_spine_items(output_path, spine_items)
        if nav_landmarks is None:
            nav_landmarks = C.nav_landmarks_from_spine_items(output_path, spine_items)
        if nav_page_list is None:
            nav_page_list = C.nav_page_list_from_spine_items(output_path, spine_items)
        navfn = C.make_nav_file(output_path, nav_toc, nav_landmarks, nav_page_list,
                                    nav_href=nav_href, title=nav_title)

        # ncx file
        ncx_fn = C.make_ncx_file(output_path, navfn, opf_metadata)
        ncx_href = os.path.normpath(os.path.relpath(ncx_fn, output_path)).replace(os.path.sep, '/')
        
        # manifest
        if manifest is None: 
            manifest = C.opf_manifest(output_path, opf_name=epub_name, cover_src=cover_src, nav_href=nav_href)

        if spine_items is None:
            spine_items = C.spine_items_from_manifest(output_path, manifest)

        # spine, with toc="ncx_id"
        spine = C.opf_spine(output_path, spine_items=spine_items, manifest=manifest, ncx_href=ncx_href)

        # guide
        guide = C.opf_guide(output_path, cover=cover_html_relpath, toc=os.path.relpath(navfn, output_path))

        # opf file -- pull it all together
        opffn = C.make_opf_file(output_path, 
                    opf_name=epub_name, metadata=opf_metadata, 
                    manifest=manifest, spine=spine, guide=guide)

        if show_nav==True:
            C.unhide_toc(os.path.join(output_path, nav_href))
            C.append_toc_to_spine(opffn, nav_href)

        mimetype_fn = C.make_mimetype_file(output_path)
        container_fn = C.make_container_file(output_path, opffn)
        
        result = Dict(
            fn=C.epub_fn(output_path, epub_name))
        if before_compile is not None:
            before_compile(output_path)
        if zip==True:
            the_epub = C.zip_epub(output_path, 
                epubfn=result.epubfn,
                mimetype_fn=mimetype_fn,
                container_fn=container_fn,
                opf_fn=opffn)
            if check==True:
                epubcheckfn = the_epub.check()
                log.debug(epubcheckfn)
                result.log = epubcheckfn
            result.fn = the_epub.fn
        else:
            result.fn = output_path
        return result

    @classmethod
    def make_cover_html(C, output_path, cover_src):
        cover_html = XML(fn=os.path.join(os.path.dirname(FILENAME), 'templates', 'cover.xhtml'))
        cover_html_relpath = os.path.splitext(cover_src)[0]+'.xhtml'
        cover_html.fn = os.path.join(output_path, cover_html_relpath)
        img = XML.find(cover_html.root, "//html:img", namespaces=EPUB.NS)
        img.set('src', os.path.basename(cover_src))
        cover_html.write(doctype="<!DOCTYPE html>")
        return cover_html.fn

    @classmethod
    def href_to_id(C, href):
        return String(href).identifier()

    @classmethod
    def epub_name_from_path(C, output_path):
        return os.path.basename(os.path.normpath(output_path).rstrip(os.path.sep))

    @classmethod
    def epub_fn(C, output_path, epub_name=None, ext='.epub'):
        return os.path.join(os.path.dirname(os.path.abspath(output_path)), 
                            (epub_name or os.path.basename(output_path.rstrip(os.path.sep)))+ext)

    @classmethod
    def opf_manifest(C, output_path, opf_name=None, nav_href=None, cover_src=None,
                        exclude=['mimetype', '*.xml', '*.opf', '.*', '~*', '#*#']):
        """build and return an opf:manifest element
        opf_name    = the relative path to the opf file
        nav_href    = the relative path (href) to the nav.xhtml file
        cover_src  = the relative path (src) to the cover image file
        """
        excludefns = []
        for excl in exclude:
            excludefns += [os.path.normpath(fn) for fn in rglob(output_path, excl)]

        if opf_name == None: 
            opf_name = os.path.basename(os.path.abspath(output_path))
        opf_path = os.path.dirname(os.path.join(output_path, opf_name + '.opf'))
        manifest = C.OPF.manifest('\n\t')
        for walk_tuple in os.walk(output_path):
            dirpath = os.path.normpath(walk_tuple[0])
            if dirpath in excludefns: continue
            for fp in walk_tuple[-1]:
                fn = os.path.normpath(os.path.join(dirpath, fp))
                if fn in excludefns: continue
                href = os.path.normpath(os.path.relpath(fn, opf_path)).replace(os.path.sep,'/')
                item = C.opf_manifest_item(opf_path, href)
                if href == nav_href:
                    item.set('properties', 'nav')
                elif href == cover_src:
                    item.set('properties', 'cover-image')
                manifest.append(item)
        return manifest  

    @classmethod
    def opf_manifest_item(C, opf_path, href, mediatype=None):
        item = C.OPF.item({
            'id': C.href_to_id(href),
            'href': href,
            'media-type': mediatype or mimetypes.guess_type(os.path.join(opf_path, href))[0]
                        or C.MEDIATYPES.get(os.path.splitext(href)[1])
                        or ''
            })
        item.tail = '\n\t'
        return item

    @classmethod
    def spine_items_from_manifest(C, output_path, manifest):
        """A list of spine_item dicts (see spec above under EPUB.build())"""
        spine_items = []
        for item in [item for item in manifest.getchildren() if item.get('href')[-4:]=='html']:
            spine_item = Dict(href=item.get('href'), idref=item.get('id'))
            # transfer relevant properties to the spine
            if 'cover-image' in item.get('properties'):
                spine_item.landmark = 'cover'
            # try to retrieve a title for this spine_item from the HTML source
            try:        
                x = XML(fn=os.path.join(output_path, spine_item.href))
                title_elems = x.root.xpath("//html:title[text()!='']", namespaces=C.NS)
                if len(title_elems) > 0:
                    spine_item.title = title_elems[0].text
            except:
                pass    # no harm in trying
            spine_items.append(spine_item)
        return spine_items

    @classmethod
    def make_nav_file(C, output_path, *nav_elems, 
                        nav_href='_nav.xhtml', title="Navigation"):
        """create a nav.xhtml file in output_path, return the filename to it"""
        H = Builder(default=C.NS.html, **{'html':C.NS.html, 'epub':C.NS.epub})._
        nav = XML(
                root=H.html(
                        '\n\t',
                        H.head('\n\t\t', 
                            H.title(title), 
                            '\n\t\t',
                            H.style("""li {list-style-type: none;}""", 
                                type="text/css"),
                            '\n\t'),
                        '\n\t', 
                        H.body('\n', *nav_elems)))
        nav.fn=os.path.join(output_path,nav_href)
        nav.write(doctype="<!DOCTYPE html>")
        return nav.fn

    @classmethod
    def nav_toc_from_spine_items(C, output_path, spine_items, nav_title="Table of Contents", hidden=""):
        nav_items = []
        for spine_item in spine_items:
            # either a title or a landmark in the spine item qualifies it for inclusion in the TOC
            item_title = spine_item.get('title') or String(spine_item.get('landmark') or '').titleify()
            if item_title not in [None, '']:
                nav_item = Dict(
                    href=spine_item.get('href'), 
                    title=item_title)
                nav_items.append(nav_item)
        if len(nav_items) > 0:
            return C.nav_elem(*nav_items, epub_type="toc", title=nav_title, hidden=hidden)

    @classmethod
    def nav_landmarks_from_spine_items(C, output_path, spine_items, title="Landmarks", hidden=""):
        """build nav landmarks from spine_items. Each spine_item can have an optional landmark attribute,
            which if given is the epub_type of that landmark.
        """
        landmarks = [
            Dict(href=spine_item.get('href'), 
                    title=spine_item.get('title'),
                    epub_type=spine_item.get('landmark'))
            for spine_item in spine_items if spine_item.get('landmark') is not None
        ]
        if len(landmarks) > 0:
            return C.nav_landmarks(*landmarks, title=title, hidden=hidden)


    @classmethod
    def nav_landmarks(C, *landmarks, title='Landmarks', hidden=""):
        """builds a landmarks nav element from the given landmarks parameters. Each parameter is a dict:
            'epub_type' : the epub:type attribute, which is the landmark type
            'href'      : the href to the landmark
            'title'     : the text to display for this landmark
        Common landmarks include: (see http://www.idpf.org/accessibility/guidelines/content/nav/landmarks.php)
            cover, toc, 
            title-page, 
            frontmatter, bodymatter, backmatter,  
            loi (list of illustrations), 
            lot (list of tables), 
            preface, bibliography, index, glossary, acknowledgments 
        """
        return C.nav_elem(*landmarks, epub_type='landmarks', title=title, hidden=hidden)

    @classmethod
    def nav_page_list_from_spine_items(C, output_path, spine_items, title="Page List", hidden=""):
        """builds a page-list nav element from the content listed in the manifest."""
        page_list_items = []
        for spine_item in spine_items:
            href = spine_item.get("href")
            fn=os.path.join(output_path, href)
            if os.path.splitext(fn)[1] not in ['.html', '.xhtml']: 
                continue
            for pagebreak in XML(fn=fn).root.xpath("//*[@epub:type='pagebreak']", namespaces=C.NS):
                page_list_items.append({
                    'href':href+'#'+pagebreak.get('id'), 
                    'title':pagebreak.get('title')})
        if len(page_list_items) > 0:
            return C.nav_elem(*page_list_items, epub_type='page-list', title=title, hidden=hidden)

    @classmethod
    def nav_elem(C, *nav_items, epub_type=None, title=None, hidden=""):
        """create and return an html:nav element.

        nav_items   = a list of dict-type elements with the following attributes:
            href        : the href to the nav item (required)
            title       : the text to display in the nav item (required)
            epub_type   : if given, the epub:type for the nav item <a> element (for landmarks nav)

        epub_type   = the epub:type attribute of the nav element
        title       = the optional title text to display on this nav
        hidden      = whether or not the nav element should be hidden; default not specified (None)
        """
        H = Builder(default=C.NS.html, **{'html':C.NS.html, 'epub':C.NS.epub})._
        if title is not None:
            h1 = H.h1(title)
        else:
            h1 = ''
        nav_elem = H.nav('\n\t', h1, '\n\t', H.ol(), '\n'); nav_elem.tail = '\n\n'
        if epub_type is not None: 
            nav_elem.set('{%(epub)s}type' % C.NS, epub_type)
        if hidden is not None: 
            nav_elem.set('hidden', hidden)
        ol_elem = nav_elem.find("{%(html)s}ol" % C.NS)
        for nav_item in nav_items:
            a_elem = H.a({'href': nav_item.get('href')}, 
                nav_item.get('title') or String(nav_item.get('epub_type')).titleify())
            if nav_item.get('epub_type') is not None: 
                a_elem.set("{%(epub)s}type" % C.NS, nav_item.get('epub_type'))
            li = H.li(a_elem); li.tail = '\n\t\t'
            ol_elem.append(li)
        return nav_elem

    @classmethod
    def make_ncx_file(C, output_path, nav_fn, metadata):
        """use the nav file and metadata to create an ncx file"""
        N = Builder(**C.NS).ncx
        nav = XML(fn=nav_fn)

        title = metadata.find("{%(dc)s}title" % C.NS)
        if title is not None:
            docTitle = title.text or ''

        authors = "; ".join(
            [c.text for c in metadata.xpath("dc:creator", namespaces=C.NS)
                # a very conservative match requirement for authors. Should this be loosened up?
                # should this query be encapsulated in the Metadata class?
                if c.xpath("""following-sibling::opf:meta[
                                contains(@refines,'%s')
                                and text()='A01']""" % c.get('id'), namespaces=C.NS)])
        
        identifier = metadata.find("{%(dc)s}identifier" % C.NS)
        if identifier is not None:
            dtb_uid = identifier.text or ''
        else:
            dtb_uid = ''

        xml_lang = metadata.find("{%(dc)s}language" % C.NS).text
        ncx = XML(
                fn=os.path.splitext(nav_fn)[0] + '.ncx',
                root=N.ncx({'version':'2005-1', '{%(xml)s}lang' % C.NS: xml_lang},
                        N.head(
                            N.meta({'name':'dtb:depth', 'content':'1'}),
                            N.meta({'name':'dtb:uid', 'content': dtb_uid})),
                        N.docTitle(N.text(docTitle)),
                        N.docAuthor(N.text(authors)),
                        N.navMap()
                        ))

        navMap = ncx.root.find("{%(ncx)s}navMap" % C.NS)
        playOrder = 0
        for a in nav.root.xpath("//html:nav[@epub:type='toc']//html:li/html:a[@href]", namespaces=C.NS):
            playOrder += 1
            href = a.get('href')
            navPoint = N.navPoint({'id': String(href).identifier(), 'playOrder': "%d" % playOrder},
                            N.navLabel(N.text(a.text)),
                            N.content({'src': href}))
            navMap.append(navPoint)

        # add page list if present
        nav_page_list = nav.root.find(".//{%(html)s}nav[@{%(epub)s}type='page-list']")
        if nav_page_list is not None:
            pageList = N.pageList(N.navLabel(N.text('Page List')))
            playOrder = 0
            for a in nav_page_list.xpath(".//a[@href]"):
                playOrder += 1
                pageList.append(
                    N.pageTarget({
                            'type': 'normal',
                            'id': C.href_to_id(a.get('href')),
                            'value': a.text,
                            'playOrder': str(playOrder)},
                        N.navLabel(N.text(a.text)),
                        N.content(src=a.get('href'))
                        ))
            ncx.root.append(pageList)

        ncx.write()
        return ncx.fn

    @classmethod
    def opf_guide(C, output_path, **references):
        guide = C.OPF.guide('\n\t\t')
        guide.tail = '\n\n'
        for key in [key for key in references.keys() if references[key] is not None]:
            ref = C.OPF.reference(type=key, title=String(key).titleify(), href=references[key])
            ref.tail = '\n\t\t'
            guide.append(ref)
        return guide

    @classmethod
    def make_opf_file(C, output_path, opf_name=None, metadata=None, manifest=None, spine=None, guide=None):
        """create an opf file in output_path, return the filename to it
        output_path   = the filesystem path in which the epub is being built (required)
        opf_name    = the relative path to the opf file in output_path; default output_path basename
        metadata    = the opf:metadata element (required)
        manifest    = an opf:manifest element
        spine       = an opf:spine element; if None, use all (x)html files in output_path.
        """
        if metadata is None or manifest is None or spine is None: 
            raise ValueError("opf:metadata, opf:manifest, and opf:spine are required to make opf package file")
        if opf_name == None: 
            opf_name = os.path.basename(os.path.abspath(output_path))
        
        xml_lang = metadata.find("{%(dc)s}language" % C.NS).text
        opffn = os.path.join(output_path, opf_name+'.opf')
        metadata.tail = '\n\n\t'
        manifest.tail = '\n\n\t'
        opfdoc = XML(
            fn=opffn, 
            root=C.OPF.package(
                    {'version':'3.0', '{%(xml)s}lang' % C.NS: xml_lang,
                    'prefix': "ibooks: http://vocabulary.itunes.apple.com/rdf/ibooks/vocabulary-extensions-1.0/"},
                    '\n\t',
                    metadata, 
                    manifest, 
                    spine, '\n\n'
                ))

        # make sure unique-identifier is set
        if metadata.find("{%(dc)s}identifier" % C.NS) is not None:
            opfdoc.root.set('unique-identifier',
                metadata.find("{%(dc)s}identifier" % C.NS).get('id'))

        # make sure there are dc:rights
        if metadata.find("{%(dc)s}rights" % C.NS) is None:
            rights = etree.Element("{%(dc)s}rights" % C.NS)
            rights.text = "All rights reserved."
            metadata.append(rights)

        if guide is not None:
            opfdoc.root.append(guide)

        opfdoc.write()
        return opfdoc.fn
    
    @classmethod    
    def opf_package_metadata(C, metadata, xml_lang='en-US', cover_src=None):
        """make adjustments to (a deep copy of) the metadata for the opf:package context"""
        DC = Builder(default=C.NS.dc, **C.NS)._
        metadata_elem = deepcopy(metadata)

        # dc:identifier is required; create UUID if not given
        if metadata_elem.find("{%(dc)s}language" % C.NS) is None:
            from uuid import uuid4
            uuid = str(uuid4())
            metadata_elem.append(DC.identifier(uuid, id='uuid'))

        # dc:language is required
        if metadata_elem.find("{%(dc)s}language" % C.NS) is None:
            metadata_elem.append(DC.language(xml_lang))

        # dc:date cannot have certain attribs: xsi:type
        for date_elem in metadata_elem.xpath("dc:date", namespaces=C.NS):
            popped = Dict()
            for k in [k for k in date_elem.attrib.keys() 
                        if k not in ALLOWED_DATE_PROPERTIES]:
                popped[k] = date_elem.attrib.pop(k)
            # if len(popped.keys()) > 0:
            #     log.warn("attributes removed from dc:date:", popped)

        # only certain non-namespaced opf:meta @property values are allowed in EPUB3
        for meta_elem in metadata_elem.xpath("opf:meta[@property]", namespaces=C.NS):
            if meta_elem.get('property') not in ALLOWED_META_PROPERTIES \
            and ':' not in (meta_elem.get('property') or ''):
                metadata_elem.remove(meta_elem)
                # log.warn("meta @property removed: %s = %s" 
                #     % (meta_elem.get('property'), meta_elem.text or ''))

        # opf:meta @property="dcterms:modified" is required; set to the current time UTC
        modified = metadata_elem.find("{%(opf)s}meta[@property='dcterms:modified']" % C.NS)
        if modified is None:
            modified = C.OPF.meta({'property': 'dcterms:modified'})
            metadata_elem.append(modified)
        modified.text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # include a <meta name="cover"...> element if cover_src is given
        if cover_src is not None and metadata_elem.find("meta[@name='cover']") is None:
            cover = C.OPF.meta({'name': 'cover', 'content': C.href_to_id(cover_src)})
            metadata_elem.append(cover)
     
        # add the ibooks specified fonts instruction to the end of the metadata section if not present
        if metadata_elem.find("meta[@property='ibooks:specified-fonts']") is None:
            metadata_elem.append(C.OPF.meta({'property':'ibooks:specified-fonts'}, 'true'))

        return metadata_elem
    
    @classmethod
    def opf_spine(C, output_path, spine_items=None, manifest=None, ncx_href=None):
        """create and return an opf:spine element
        output_path   = the filesystem path in which the epub is being built (required)
        spine_items = a list of dicts that has spine item attributes; or build from opf:manifest
        manifest    = an opf:manifest to build the spine from (if spine_items not given)
        ncx_href    = if given, used to add the toc attribute to the spine
        """
        if spine_items is not None:
            spine = C.OPF.spine('\n\t\t', *[C.opf_spine_itemref(spine_item) for spine_item in spine_items])
        elif manifest is not None: 
            spine = C.OPF.spine(*[C.OPF.itemref(idref=item.get('id')) for item in manifest.getchildren()])
        else:
            raise ValueError("either spine_items (a list) or manifest (opf:manifest element) must be provided to EPUB.opf_spine()")
        for ch in spine.getchildren(): 
            ch.tail='\n\t\t'
        if ncx_href is not None:
            spine.set('toc', C.href_to_id(ncx_href))
        return spine

    @classmethod
    def opf_spine_itemref(C, spine_item):
        """create an opf:itemref for the opf:spine from the given spine_item, with the following attributes:
        href        : if given, is converted to the idref using href_to_id()
        idref       : if given (and no href), is used as the idref
        linear      : if given, becomes the "linear" property ("yes|no")
        properties  : if given, space-separated list of spine itemref properties
        """
        itemref = C.OPF.itemref({
                'idref': spine_item.get('idref')        # use @idref if given
                        or (spine_item.get('href')      # otherwise generate from @href
                            and C.href_to_id(spine_item.get('href')))
            })

        if spine_item.get('linear') is not None:
            itemref.set('linear', spine_item.get('linear'))
        if spine_item.get('properties') is not None:
            itemref.set('properties', spine_item.get('properties'))
        return itemref

    @classmethod
    def make_mimetype_file(C, output_path, mimetype=None):
        """create a mimetype file in output_path"""
        if mimetype is None: mimetype = C.MEDIATYPES.get('.epub')
        t = Text(fn=os.path.join(output_path, 'mimetype'),
            text=mimetype, encoding='ascii')
        t.write()
        return t.fn

    @classmethod
    def make_container_file(C, output_path, *opf_fns):
        """given an output_path and a list of opf_fns, create a META-INF/container.xml file"""
        Container = Builder(default=C.NS.container, **C.NS)._
        x = XML(fn=os.path.join(output_path, 'META-INF', 'container.xml'),
                root=Container.container(
                        {'version':'1.0'},
                        Container.rootfiles(*[
                            Container.rootfile(
                                {'full-path': os.path.normpath(os.path.relpath(opf_fn, output_path)).replace(os.path.sep,'/'),
                                'media-type': C.MEDIATYPES.get('.opf')})
                            for opf_fn in opf_fns
                            ]))
            )
        x.write()
        return x.fn

    @classmethod
    def unhide_toc(C, navfn):
        """the toc in the nav_toc.xhtml file should NOT be hidden"""
        toc = XML(fn=navfn)
        nav = XML.find(toc.root, "html:body/html:nav[@epub:type='toc']", namespaces=C.NS)
        if nav is not None and 'hidden' in nav.attrib:
            _ = nav.attrib.pop('hidden')
        toc.write()

    @classmethod
    def append_toc_to_spine(C, opffn, nav_href):
        """nav html needs to be in spine in order for Kindle to display a TOC"""
        from .epub import EPUB
        x = XML(fn=opffn)
        nav_id = EPUB.href_to_id(nav_href)
        spine = XML.find(x.root, "opf:spine", namespaces=C.NS)
        spine_item = XML.find(spine, "opf:itemref[@idref='%s']" % nav_id, namespaces=C.NS)
        if spine_item is None:
            itemref = etree.Element("{%(opf)s}itemref" % C.NS, idref=nav_id); itemref.tail='\n\t\t'
            spine.append(itemref)
            x.write()

    @classmethod
    def zip_epub(C, output_path, epubfn=None, mimetype_fn=None, opf_fn=None, container_fn=None, other_fns=[],
                compression=zipfile.ZIP_DEFLATED):
        """zip the epub and return its filename"""
        # set up the .zip file
        epub = ZIP(fn=epubfn or C.epub_fn(output_path), mode='w', compression=compression)
        log.info("epub: %s" % epub.fn)

        # mimetype must be first, and not be compressed
        if mimetype_fn is None:
            mimetype_fn = C.make_mimetype_file(output_path)
        epub.zipfile.write(mimetype_fn, os.path.relpath(mimetype_fn, output_path), compress_type=zipfile.ZIP_STORED)
        
        if opf_fn is None:
            opf_fn = C.get_opf_fn(output_path)
        epub.zipfile.write(opf_fn, os.path.relpath(opf_fn, output_path))

        if container_fn is None:
            container_fn = C.make_container_file(output_path, opf_fn)
        epub.zipfile.write(container_fn, os.path.relpath(container_fn, output_path))

        # write everything listed in opf:manifest
        opf = XML(fn=opf_fn or C.get_opf_fn(output_path))
        for item in opf.root.xpath("opf:manifest/opf:item", namespaces=C.NS):
            href = item.get('href')
            fn = os.path.join(output_path, href)
            epub.zipfile.write(fn, os.path.relpath(fn, output_path))

        # write other_fns, such as special contents of META-INF
        for fn in other_fns:
            epub.zipfile.write(other_fn, os.path.relpath(fn, output_path))

        epub.close()
        the_epub = C(fn=epub.fn)
        return the_epub

    @classmethod
    def get_opf_fn(C, output_path):
        "from a given output_path, return the first opf_fn from META-INF/container.xml"
        container = XML(fn=os.path.join(output_path, 'META-INF', 'container.xml'))
        rootfile = container.root.find("{%(container)s}rootfiles/{%(container)s}rootfile[@full-path]" % C.NS)
        if rootfile is not None:
            return os.path.join(output_path, rootfile.get('full-path'))

    @classmethod
    def get_nav_fn(C, output_path):
        opffn = C.get_opf_fn(output_path)
        if opffn is not None:
            opf = XML(fn=opffn)
            nav_item = opf.root.find(".//{%(opf)s}item[@properties='nav']" % C.NS)
            if nav_item is not None:
                navfn = os.path.abspath(os.path.join(os.path.dirname(opffn), nav_item.get('href')))
                return navfn
    
if __name__=='__main__':
    import sys
    if len(sys.argv) > 1:
        if 'zip' in sys.argv[1]:
            for path in sys.argv[2:]:
                EPUB.zip_epub(path)
        if 'check' in sys.argv[1]:
            for fn in sys.argv[2:]:
                EPUB(fn=fn).check()
        if 'unzip' in sys.argv[1]:
            for fn in sys.argv[2:]:
                EPUB(fn=fn).unzip()
