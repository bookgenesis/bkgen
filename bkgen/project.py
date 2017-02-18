
import logging
log = logging.getLogger(__name__)

import os, re, shutil, subprocess, sys, time, traceback
from copy import deepcopy
from bl.file import File
from bl.string import String
from bl.rglob import rglob
from bxml.xml import XML, etree
from bl.text import Text
from bl.dict import Dict
from bl.zip import ZIP

from pubxml.idml import IDML

import bg
from .account import Account
from .document import Document
from .icml import ICML
from .docx import DOCX

FILENAME = os.path.abspath(__file__)

class Project(XML):
    """Every project has a project.xml file that holds information about the project.
        (The project itself is the folder in which the project.xml file occurs.)
    """
    ROOT_TAG = "{%(pub)s}project" % bg.NS
    EXPORT_KINDS = ['EPUB', 'Kindle', 'Archive']

    def __repr__(self):
        return "Project(%s)" % self.fn

    def name(self):
        return self.root.get('name')

    def account_id(self):
        return os.path.basename(os.path.dirname(self.dirpath()))

    def excerpt(self, db, content_href=None):
        _excerpts = self.excerpts(db, content_href=content_href)
        if len(_excerpts) > 0:
            return _excerpts[0]

    def excerpts(self, db, content_href=None, orderby="inserted desc"):
        from .excerpt import Excerpt
        return Excerpt(db).select(
            account_id=self.account_id(), project_name=self.name(), content_href=content_href,
                orderby=orderby)

    @classmethod
    def create(C, parent_path, title, name=None, template_name='Base', db=None, **Accounts):
        """create a new project.
            parent_path = the filesystem path to the parent folder that this project is in
            name = the name of the project, which becomes its folder name and URL slug
            **Accounts = contents of the "Accounts" configuration block.
                templates = the installation path for the Templates account
        Returns the Project XML object.
        """
        name = name or String(title).nameify()
        if not os.path.exists(parent_path):
            raise ValueError("Before creating a project in %s, first create the parent folder." % parent_path)

        project_path = os.path.join(parent_path, name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        else:
            log.info("Project folder already exists: %s" % project_path)

        template = C(fn=os.path.join(Accounts.get('templates'), template_name, 'project.xml'))
        if not os.path.exists(template.fn):
            template = XML(fn=os.path.join(os.path.abspath(os.path.dirname(__file__)), 
                            'templates', 'project.xml'))

        # project.xml
        project_fn = os.path.join(project_path,'project.xml')
        if os.path.exists(project_fn):
            log.info("Project file already exists, not overwriting: %s" % project_fn)
            p = Project(fn=project_fn)
        else:        
            p = Project(fn=project_fn, root=deepcopy(template.root))
            p.root.set('name', name)
            p.find(p.root, "opf:metadata/dc:title", namespaces=bg.NS).text = title

        # make sure there is a stylesheet resource for this project
        resources = p.find(p.root, "pub:resources", namespaces=bg.NS)
        stylesheet_href = os.path.join(
            os.path.relpath(p.content_path(), p.dirpath()), 
            p.name()+'.css')
        
        stylesheet_elem = p.find(resources, 
            "pub:resource[@class='stylesheet']", namespaces=bg.NS)
        if stylesheet_elem is None:
            stylesheet_elem = etree.Element("{%(pub)s}resource" % bg.NS, 
                **{'class':'stylesheet'})
            stylesheet_elem.tail='\n\t'
            resources.insert(0, stylesheet_elem)        # the base stylesheet is always first
        stylesheet_elem.set('href', stylesheet_href)

        if db is not None:
            p.make_resource_excerpts(db, content_href=stylesheet_href)

        stylesheet_fn = os.path.join(p.dirpath(), stylesheet_elem.get('href'))
        if not os.path.exists(stylesheet_fn):
            template_href = template.find(template.root, 
                "pub:resources/pub:resource[@class='stylesheet']/@href", namespaces=bg.NS)
            if template_href is not None:
                template_fn = os.path.join(template.dirpath(), template_href)
            else: 
                template_fn = stylesheet_fn
            s = Text(fn=template_fn)
            if s.text == '':
                log.warn('stylesheet does not exist at %s -- making blank base stylesheet' % s.fn)
            s.write(fn=stylesheet_fn)

        p.write()
        return p

    def import_source(self, source, db=None, with_metadata=True, **params):
        """import a source into the project.
            source : an object that contains the content source; must have the following interface:
                source.fn               -- the current full filename of the source
                source.write(fn=...)    -- to write the content source 
                source.documents(path=...) -- to return a collection of <pub:document/> containing the content
                source.resources(path=...) -- to return a collection of files containing resources
                source.metadata()       -- to return an <opf:metadata/> element containing source metadata
                source.stylesheet()     -- to return a CSS stylesheet.
            db     : the database in which excerpt references are to be stored
        """
        if self.dirpath() in os.path.commonprefix([self.fn, source.fn]):
            # source is inside the project directory, use it in locu
            source_href = os.path.relpath(source.fn, os.path.commonpath([self.fn, source.fn]))
        else:
            # save the source into the "sources" directory
            basename = re.sub("(&[\w^;]+;|[\s\&+;'])", "-", os.path.basename(source.fn))
            src_fn = os.path.join(self.dirpath(), 'sources', basename)
            source_href = os.path.relpath(src_fn, self.dirpath()).replace('\\', '/')
            source.write(fn=src_fn)

        # add the source to the sources element, if it's not already there.
        sources_elem = self.root.find("{%(pub)s}sources" % bg.NS)
        s = XML.find(sources_elem, "pub:source[@href='%s']" % source_href, namespaces=bg.NS)
        if s is None:
            s = etree.Element("{%(pub)s}source" % bg.NS, 
                    href=source_href)
            s.tail = '\n\t'
            sources_elem.append(s)
        s.set('imported', time.strftime("%Y-%m-%dT%H:%M:%S"))

        # convert the source to a collection of pub:document 
        # -- any source object must have a documents() method
        # store each pub:document, overwriting any file with the same name.
        documents_elem = self.root.find("{%(pub)s}documents" % bg.NS)
        documents = source.documents(path=self.content_path(), **params)
        for doc in documents:
            doc_href = os.path.relpath(doc.fn, self.dirpath()).replace('\\', '/')
            doc_id = String(doc_href).identifier()
            doc.write()

            # update the documents element
            d = XML.find(documents_elem, "pub:document[@href='%s']" % doc_href, namespaces=bg.NS)
            if d is None:
                d = etree.Element("{%(pub)s}document" % bg.NS, 
                    attrib={'href':doc_href, 'source':source_href})
                d.tail = '\n\t'
                documents_elem.append(d)

            # update the spine element
            # -- append anything that is new.
            sections = doc.root.xpath("html:body/html:section[@id]", namespaces=bg.NS)
            spine_elem = self.root.find("{%(pub)s}spine" % bg.NS)
            spine_hrefs = [
                se.get('href') for se in 
                spine_elem.xpath("pub:spineitem[contains(@href, '%s')]" % doc_href, 
                    namespaces=bg.NS)]
            for section in sections:
                href = doc_href+'#'+section.get('id')
                title = section.get('title') or ''
                if href not in spine_hrefs:
                    spineitem = etree.Element(
                        "{%(pub)s}spineitem" % bg.NS, 
                        attrib={
                            'href':href, 
                            'title':section.get('title') or ''
                        })
                    if section.get('landmark') is not None:
                        spineitem.set('landmark', section.get('landmark'))
                    spineitem.tail = '\n\t'
                    spine_elem.append(spineitem)

        # write any stylesheet for the source
        try:
            css = source.stylesheet(fn='/'.join([self.content_path(), os.path.splitext(os.path.basename(source.fn))[0]+'.css']))
            css.write()
        except:
            log.warn(sys.exc_info()[1])
            log.debug(traceback.format_exc())

        # get any resources from the source
        resources = self.find(self.root, "pub:resources", namespaces=bg.NS)
        for resource in source.resources(path=self.content_path()):
            log.debug(resource.fn)
            href = os.path.relpath(resource.fn, os.path.dirname(self.fn))
            resource_elem = self.find(resources, "pub:resource[@href='%s']" % href, namespaces=bg.NS)
            if resource_elem is None:
                resource_elem = etree.Element("{%(pub)s}resource" % bg.NS, href=href)
                resource_elem.tail = '\n\t'
                resources.append(resource_elem)
            if resource.get('class') is not None: 
                resource_elem.set('class', resource.get('class'))
            else:
                if 'image' in (resource.mediatype or ''):
                    resource_elem.set('class', 'image')
                elif 'css' in (resource.mediatype or ''):
                    resource_elem.set('class', 'stylesheet')

        # make content excerpts
        if db is not None:
            self.make_content_excerpts(db, source_href=source_href)

        # update the project metadata from the source metadata
        if with_metadata==True:
            metadata = self.find(self.root, "opf:metadata", namespaces=bg.NS)
            for elem in source.metadata():
                tests = []
                for k in elem.attrib.keys():
                    ns = XML.tag_namespace(k)
                    if ns not in ['', None] and ns in bg.NS.values():
                        prefix = bg.NS.keys()[bg.NS.values().index(ns)]
                        key = k.replace("{%s}" % ns, prefix+':')
                    else:
                        key = k
                    value = elem.attrib[k]
                    tests.append("@%s='%s'" % (key, value))
                if elem.text is not None:
                    tests.append("text()='%s'" % elem.text)

                ns = XML.tag_namespace(elem.tag)
                if ns not in ['', None] and ns in bg.NS.values():
                    prefix = bg.NS.keys()[bg.NS.values().index(ns)]
                    tag = elem.tag.replace("{%s}" % ns, prefix+':')
                else:
                    tag = elem.tag
                if len(tests) > 0:
                    metadata_xpath = "%s[%s]" % (tag, " and ".join(tests))
                else:
                    metadata_xpath = tag
                metadata_elem = self.find(metadata, metadata_xpath, namespaces=bg.NS)
                if metadata_elem is None:
                    metadata.append(elem)

            # also make sure that each element has an id
            for elem in metadata.getchildren():
                if elem.get('id') in ['', None]:
                    ns = XML.tag_namespace(elem.tag)
                    if ns in bg.NS.values():
                        prefix = bg.NS.keys()[bg.NS.values().index(ns)]
                        tag = elem.tag.replace("{%s}" % ns, prefix+':')
                    else:
                        tag = elem.tag
                    elems = self.xpath(metadata, tag, namespaces=bg.NS)
                    id = tag.split(':')[-1]+str(elems.index(elem)+1)
                    elem.set('id', id)
        
        self.write()

    def import_metadata(self, fn):
        from .metadata import Metadata
        md = Metadata(fn=fn)
        metadata = XML.find(self.root, "opf:metadata", namespaces=bg.NS)
        for ch in md.root.getchildren():
            old_elem = XML.find(metadata, "*[@id='%s' or @property='%s']" % (ch.get('id'), ch.get('property')))
            if old_elem is not None:
                metadata.replace(old_elem, ch)
            else:
                metadata.append(ch)
        self.write()

    def import_image(self, fn, db=None, **params):
        """import the image from a local file. Process through GraphicsMagick to ensure clean."""
        basename = re.sub("(&[\w^;]+;|[\s\&+;'])", "-", os.path.basename(os.path.splitext(fn)[0]+'.jpg'))
        outfn = os.path.join(self.image_path(), basename)
        log.debug('image: %s' % os.path.relpath(fn, self.dirpath()))
        ext = os.path.splitext(fn)[-1].lower()
        if ext == '.pdf':
            from bf.pdf import PDF
            PDF(fn=fn).gswrite(fn=outfn, device='jpeg', res=600)
        else:
            from bf.image import Image
            Image(fn=fn).convert(outfn, format='jpg', quality=90)

        # move the image to the Project folder
        # and create a resource for it
        f = File(fn=outfn)
        resource_fn = os.path.join(self.image_path(), basename)
        log.debug("resource = %s" % os.path.relpath(resource_fn, self.dirpath()))

        f.write(fn=resource_fn)
        log.debug(os.path.relpath(resource_fn, self.dirpath()))
        href = os.path.relpath(resource_fn, self.dirpath())
        resource = self.find(self.root, "//pub:resource[@href='%s']" % href, namespaces=bg.NS)
        if resource is None:
            resource = etree.Element("{%(pub)s}resource" % bg.NS, **{'href':href, 'class':'image'})
            resource.tail = '\n\t'
            resources = self.find(self.root, "pub:resources", namespaces=bg.NS)
            resources.append(resource)

        if params.get('class')=='cover-digital' and os.path.splitext(resource_fn)[-1]=='.jpg':
            existing_cover_digital = self.find(self.root, 
                "//pub:resource[@class='cover-digital']", namespaces=bg.NS)
            if existing_cover_digital is not None:
                existing_cover_digital.set('class', 'image')
            resource.set('class', 'cover-digital')

        if db is not None:
           self.make_resource_excerpts(db, content_href=href)

        self.write()

    def output_path(self):
        """return the absolute path to the project outputs directory; creates the directory if needed"""
        p = os.path.join(self.dirpath(), self.output_folder or 'exports')
        if not os.path.exists(p): 
            os.makedirs(p)
        return p

    def content_path(self):
        """return the absolute path to the project content directory; creates the directory if needed"""
        p = os.path.join(self.dirpath(), self.content_folder or 'content')
        if not os.path.exists(p): 
            os.makedirs(p)
        return p

    def image_path(self):
        p = os.path.join(self.dirpath(), self.image_folder or 'images')
        if not os.path.exists(p): 
            os.makedirs(p)
        return p

    def make_content_excerpts(self, db, content_href=None, source_href=None):
        """create an excerpt in the database for every section that has an id, and every resource."""
        from .excerpt import Excerpt
        project_name = self.root.get('name')
        project_title = self.find(self.root, "//dc:title/text()", namespaces=bg.NS)
        if project_title is not None: project_title = str(project_title)
        account_id = os.path.basename(os.path.dirname(os.path.dirname(self.fn)))
        doc_xpath = "pub:documents/pub:document"
        if content_href is not None:
            doc_xpath += "[@href='%s']" % content_href
        elif source_href is not None:
            doc_xpath += "[@source='%s']" % source_href
        for doc_elem in self.xpath(self.root, doc_xpath, namespaces=bg.NS):
            doc_href = doc_elem.get('href')
            doc = Document(fn=os.path.join(os.path.dirname(self.fn), doc_href))
            for elem in doc.xpath(doc.root, "//html:section[@id]", namespaces=bg.NS):
                content_href = doc_href+'#'+elem.get('id')
                section_title = elem.get('title')
                Excerpt.create(db, account_id, project_name, content_href, 
                    text=etree.tounicode(elem, with_tail=False),
                    project_title=project_title,
                    section_title=section_title)

    def make_resource_excerpts(self, db, content_href=None):
        from .excerpt import Excerpt
        project_name = self.root.get('name')
        project_title = self.find(self.root, "//dc:title/text()", namespaces=bg.NS)
        if project_title is not None: project_title = str(project_title)
        account_id = os.path.basename(os.path.dirname(os.path.dirname(self.fn)))
        if content_href is None:
            resources = self.xpath(self.root, 
                "pub:resources/pub:resource", namespaces=bg.NS)
        else:
            resources = self.xpath(self.root, 
                "pub:resources/pub:resource[@href='%s']" % content_href, namespaces=bg.NS)
        for resource in resources:
            content_href = resource.get('href')
            Excerpt.create(db, account_id, project_name, content_href, 
                project_title=project_title)

    def build_exports(self, kind=None):
        """build the project exports, with options, based on stored parameters in project.xml
            kind=None:      which kind of output to build; if None, build all
        """
        log.info("build project exports: %s" % self.fn)
        
        exports = self.find(self.root, "pub:exports", namespaces=bg.NS)
        if exports is None:
            last = self.root.getchildren()[-1]; last.tail = '\n\n\t'
            exports = etree.Element("{%(pub)s}exports" % bg.NS); exports.tail='\n\n'; exports.text='\n\t'
            self.root.append(exports)
        exports.set('pending', 'True')
        exports.set('started', time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.write()
        
        if kind is not None: 
            export_kinds = [kind]       # build all outputs if kind is not specified
        else: 
            export_kinds = self.EXPORT_KINDS
        results = []
        for export_kind in export_kinds:
            try:
                log.info("export kind=%r" % export_kind)
                
                export = self.find(exports, "pub:export[@kind='%s']" % export_kind, namespaces=bg.NS)
                if export is None:
                    export = etree.Element("{%(pub)s}export" % bg.NS, kind=export_kind); export.tail='\n\t'
                    exports.append(export)
                self.write()

                if export_kind=='EPUB':
                    outfn = self.build_epub()
                elif export_kind=='Kindle':
                    outfn = self.build_mobi()
                elif export_kind=='Archive':
                    outfn = self.build_project_zip()
                else:
                    log.error("Unsupported export kind")
                    raise KeyError("Unsupported export kind")

                result = Dict(kind=export_kind, message="build succeeded", filename=outfn)
                
                export.set('success', "True")
                export.set('completed', time.strftime("%Y-%m-%dT%H:%M:%S"))
                export.set('href',os.path.relpath(outfn, self.dirpath()))
                if export.get('message') is not None: _=export.attrib.pop('message')
                self.write()
            except:
                msg = (str(String(sys.exc_info()[0].__name__).camelsplit()) + ' ' + str(sys.exc_info()[1])).strip()
                result = Dict(kind=export_kind, message=msg, traceback=traceback.format_exc())
                log.warn(result.msg)
                log.debug(result.traceback)

                export.set('success', "False");
                export.set('message', result.message)
                export.set('completed', time.strftime("%Y-%m-%dT%H:%M:%S"))
                self.write()

            results.append(result)

        exports.set('pending', "False")
        exports.set('completed', time.strftime("%Y-%m-%dT%H:%M:%S"))
        self.write()

        return results

    def build_project_zip(self):
        """create a zip archive of the project folder itself"""
        outfn = os.path.join(self.output_path(), self.root.get('name')+'.zip')
        return ZIP.zip_path(self.dirpath(), 
                fn=outfn,
                exclude=[os.path.relpath(outfn, self.dirpath())],           # avoid self-inclusion
                mode='w')

    def build_epub(self, clean=True, show_nav=False, zip=True, check=True, cleanup=False, **image_args):
        from .epub import EPUB
        epub_isbn = XML.find(self.root, 
            """opf:metadata/dc:identifier[
                contains(@id,'isbn') and 
                (contains(@id,'epub') or contains(@id, 'ebook'))]""", 
            namespaces=bg.NS)
        if epub_isbn is not None:
            epub_name = epub_isbn.text.replace('-', '')
        else:
            epub_name = self.root.get('name')
        epub_path = os.path.join(self.output_path(), epub_name+"_EPUB")
        if clean==True and os.path.isdir(epub_path): shutil.rmtree(epub_path)
        if not os.path.isdir(epub_path): os.makedirs(epub_path)
        resources = self.output_resources(output_path=epub_path, **image_args)
        metadata = XML.find(self.root, "opf:metadata", namespaces=bg.NS)
        cover_src = XML.find(self.root, 
            "pub:resources/pub:resource[contains(@class, 'cover-digital')]/@href", namespaces=bg.NS)
        spine_items = self.output_spineitems(output_path=epub_path, resources=resources, format='xhtml')
        epubfn = EPUB().build(epub_path, metadata, 
            epub_name=epub_name, spine_items=spine_items, cover_src=cover_src, 
            show_nav=show_nav, zip=zip, check=check)
        if cleanup==True: shutil.rmtree(epub_path)
        return epubfn

    def build_mobi(self, clean=True, cleanup=False, **image_args):
        from .mobi import MOBI
        mobi_isbn = (XML.find(self.root, 
            """opf:metadata/dc:identifier[
                contains(@id,'isbn') and 
                (contains(@id,'mobi') or contains(@id,'kindle') or contains(@id, 'ebook'))]""", 
            namespaces=bg.NS))
        if mobi_isbn is not None:
            mobi_name = mobi_isbn.text.replace('-', '')
        else:
            mobi_name = self.root.get('name')
        mobi_path = os.path.join(self.output_path(), mobi_name+"_MOBI")
        if clean==True and os.path.isdir(mobi_path): shutil.rmtree(mobi_path)
        if not os.path.isdir(mobi_path): os.makedirs(mobi_path)
        resources = self.output_resources(output_path=mobi_path, **image_args)
        metadata = self.root.find("{%(opf)s}metadata" % bg.NS)
        stylesheets = [resource.get('href') for resource in resources 
                        if resource.get('class')=='stylesheet']
        covers_digital = [resource.get('href') for resource in resources 
                        if resource.get('class')=='cover-digital']
        if len(covers_digital) > 0: cover_src = covers_digital[0]
        else: cover_src = None
        spine_items = self.output_spineitems(output_path=mobi_path, resources=resources, format='html', http_equiv_content_type=True, canonicalized=False)
        mobifn = MOBI().build(
                    mobi_path, metadata, 
                    mobi_name=mobi_name, spine_items=spine_items, cover_src=cover_src)
        if cleanup==True: shutil.rmtree(mobi_path)
        return mobifn

    def output_resources(self, output_path=None, **image_args):
        log.debug("project.output_resources()")
        if output_path is None: output_path = self.output_path()
        resources = [deepcopy(resource) 
                    for resource in 
                    self.root.xpath("pub:resources/pub:resource[not(@include='False')]", namespaces=bg.NS)]
        for resource in resources:
            f = File(fn=os.path.abspath(os.path.join(self.dirpath(), resource.get('href'))))
            if resource.get('class')=='stylesheet':
                outfn = self.output_stylesheet(f.fn, output_path)
            elif resource.get('class') in ['cover-digital', 'image']:
                outfn = self.output_image(f.fn, output_path, **image_args)
            else:                                                               # other resource as-is
                outfn = os.path.join(output_path, os.path.relpath(f.fn, os.path.dirname(self.fn)))
                f.write(fn=outfn)
            resource.set('href', os.path.relpath(outfn, output_path))
            log.debug(resource.attrib)
        return resources

    def output_stylesheet(self, fn, output_path):
        log.debug("project.output_stylesheet(fn=%r) -- exists? %s" % (fn, os.path.exists(fn)))
        f = File(fn=fn)
        outfn = os.path.join(output_path, f.relpath(dirpath=self.dirpath()))
        if f.ext() == '.scss':
            from bl.scss import SCSS
            outfn = os.path.splitext(outfn)[0]+'.css'
            css = SCSS(fn=f.fn).render_css(fn=outfn)
            css.write()
        else:
            f.write(fn=outfn)
        return outfn

    def output_image(self, fn, output_path, format='jpeg', ext='.jpg', res=300, quality=80, maxwh=2048):
        f = File(fn=fn)
        mimetype = f.mimetype() or ''
        outfn = os.path.splitext(
                    os.path.join(output_path, f.relpath(dirpath=self.dirpath()))
                )[0] + ext
        if not os.path.exists(os.path.dirname(outfn)):
            os.makedirs(os.path.dirname(outfn))
        if mimetype=='application/pdf':
            from bf.pdf import PDF
            res = PDF(fn=fn).gswrite(fn=outfn, device=format, res=res)
        elif 'image/' in mimetype:
            from bf.image import Image
            img_args=Dict(
                format=format.upper(), 
                density="%dx%d" % (res,res))
            if format.lower() in ['jpeg', 'jpg']:
                img_args.update(quality=quality)
            res = Image(fn=fn).convert(outfn, **img_args)
        else:
            res = None
        return outfn

    def output_spineitems(self, output_path=None, format='xhtml', resources=None, http_equiv_content_type=False, canonicalized=False, **image_args):
        log.debug("project.output_spineitems()")
        if output_path is None: output_path = self.output_path()
        if resources is None: resources = self.output_resources(output_path=output_path, **image_args)
        spineitems = [deepcopy(spineitem) for spineitem in 
                    self.root.xpath("pub:spine/pub:spineitem[not(@include='False')]", namespaces=bg.NS)]
        outfns = []
        for spineitem in spineitems:
            split_href = spineitem.get('href').split('#')
            docfn = os.path.join(self.dirpath(), split_href[0])
            if len(split_href)>1: 
                d = Document.load(fn=docfn, section_id=split_href[1])
            else:
                d = Document.load(fn=docfn)
            outfn = os.path.splitext(
                        os.path.join(output_path, os.path.relpath(d.fn, self.dirpath()))
                    )[0] + '.' + format
            if 'html' in format:
                # create the output html for this document
                h = d.html(fn=outfn, ext='.'+format, resources=resources, output_path=output_path, http_equiv_content_type=http_equiv_content_type)
                # add the document-specific CSS, if it exists
                doc_css_fn = os.path.splitext(docfn)[0]+'.css'
                out_css_fn = os.path.splitext(
                    os.path.join(output_path, os.path.relpath(docfn, self.dirpath())))[0]+'.css'
                if os.path.exists(doc_css_fn) and not os.path.exists(out_css_fn):
                    Text(fn=doc_css_fn).write(fn=out_css_fn)
                    # outfns.append(out_css_fn)
                if os.path.exists(out_css_fn):
                    head = XML.find(h.root, "html:head", namespaces=bg.NS)
                    href = os.path.relpath(out_css_fn, h.dirpath())
                    link = etree.Element("{%(html)s}link" % bg.NS, rel="stylesheet", href=href, type="text/css")
                    head.append(link)
                h.write(doctype="<!DOCTYPE html>", canonicalized=canonicalized)
                outfns.append(h.fn)
                spineitem.set('href', os.path.relpath(h.fn, output_path))

                # output any images that are referenced from the document and are locally available
                from bf.image import Image
                for img in h.root.xpath("//html:img", namespaces=bg.NS):
                    srcfn = os.path.join(os.path.dirname(d.fn), img.get('src'))
                    if os.path.exists(srcfn):
                        outfn = os.path.abspath(os.path.join(os.path.dirname(h.fn), img.get('src')))
                        Image(fn=srcfn).convert(outfn, format='jpg', quality=70)
                    else:
                        log.warn("NOT FOUND: %s" % srcfn)

        if 'html' in format:
            # collect the @ids from the content and fix the hyperlinks
            ids = Dict()
            for outfn in outfns:
                for elem in XML(fn=outfn).root.xpath("//*[@id]"):
                    ids[elem.get('id')] = outfn
            for outfn in outfns:
                x = XML(fn=outfn)
                # fix hyperlinks
                for e in [e for e in x.root.xpath("//*[@href]") 
                        if e.get('href') 
                        and (e.get('href')[0]=='#'
                            or ('#' in e.get('href') 
                                and e.get('href').split('#')[0] 
                                not in [os.path.basename(f) for f in outfns]))]:
                    id = e.get('href').split("#")[-1]
                    if id in ids:
                        href = os.path.relpath(ids[id], os.path.dirname(x.fn))+'#'+id
                        e.set('href', href)
                # images will be jpegs
                for e in x.root.xpath("//html:img[@src]", namespaces=bg.NS):
                    e.set('src', os.path.splitext(e.get('src'))[0]+'.jpg')
                x.write()
        return spineitems

    def get_scss(self, output_path=None):
        """returns a list of SCSS objects for the project, based on the stylesheet values in resources"""
        from bl.scss import SCSS
        output_path = output_path or self.dirpath()
        scss_docs = [
            SCSS(fn=os.path.join(self.dirpath(), resource.get('href')))
            for resource in 
            self.root.xpath("//pub:resource[@class='stylesheet' and contains(@href, '.scss')]", 
                namespaces=bg.NS)
        ]
        return scss_docs

    def make_css(self, output_path=None):
        """returns a list of CSS objects rendered from scss"""
        output_path = output_path or self.dirpath()
        css_docs = [
            sc.render_css(
                fn=os.path.join(
                    output_path, 
                    os.path.splitext(os.path.relpath(sc.fn, self.dirpath()))[0]+'.css')) 
            for sc in 
            self.get_scss()
        ]
        return css_docs

def create_project(path, config=bg.config, db=None):
    """create the project in the given folder."""
    parent_path = os.path.dirname(path)
    name = os.path.basename(path)
    title = String(' '.join(name.split('_')[-1:])).camelsplit()
    account_id = os.path.basename(parent_path)
    if db is not None:
        account = Account(db).select_one(id=account_id) or Account.create(db, account_id, **config.Accounts)
    log.info("== CREATE PROJECT: %s" % name)
    project = Project.create(parent_path, title, name=name, **config.Accounts)
    for folder in ['cover', 'sources', 'ebooks']:
        folderpath = os.path.join(parent_path, name, folder)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)        

def import_all(path, config=bg.config, db=None):
    """import sources, cover, and metadata into project"""
    project = Project(fn=os.path.join(path, 'project.xml'), **config.Projects)
    basename = os.path.basename(project.dirpath())
    log.info("== IMPORT ALL FOR PROJECT: %s" % basename)
    try:
        interior_path = glob(os.path.join(project.dirpath(), '*_int'))[0]
    except:
        try:
            interior_path = glob(os.path.join(project.dirpath(), '*interior*'))[0]
        except:
            interior_path = os.path.join(project.dirpath(), 'interior')
    if not os.path.exists(interior_path):
        os.makedirs(interior_path)
    sources_path = os.path.join(project.dirpath(), 'sources')
    if not os.path.exists(sources_path): os.makedirs(sources_path)
    cover_path = os.path.join(project.dirpath(), 'cover')
    if not os.path.exists(cover_path): os.makedirs(cover_path)
    # icml 
    fns = rglob(interior_path, '*.icml') + rglob(sources_path, '*.icml')
    log.info('-- %d .icml files' % len(fns))
    for fn in fns: 
        project.import_source(ICML(fn=fn), fns=fns, db=db)
    # idml if available
    log.info('-- %d .idml files' % len(fns))
    fns = rglob(interior_path, '*.idml') + rglob(sources_path, '*.idml')
    for fn in fns:
        project.import_source(IDML(fn=fn), fns=fns, db=db)
    # docx
    fns = rglob(interior_path, '*.docx') + rglob(sources_path, '*.docx')
    log.info('-- %d .docx files' % len(fns))
    for fn in fns:
        project.import_source(DOCX(fn=fn), db=db, with_metadata=False)
    # metadata.xml
    fns = [fn for fn in rglob(project.dirpath(), '*metadata.xml')
            if '.itmsp' not in fn]      # not inside an iTunes Producer package
    log.info('-- %d metadata.xml files' % len(fns))            
    for fn in fns:
        project.import_metadata(fn, db=db)
    # images
    fns = [fn for fn in rglob(interior_path+'/Links', "*.*")
        if os.path.splitext(fn)[-1].lower() in ['.pdf', '.jpg', '.png', '.tif', '.tiff', '.eps']]
    log.info('-- %d image files' % len(fns))
    for fn in fns:
        project.import_image(fn, db=db)
    # cover
    fns = rglob(cover_path, "*.jpg")
    if len(fns) > 0:
        project.import_image(fns[0], db=db, **{'class': 'cover-digital'})

def build_project(path, format=None, config=bg.config):
    project = Project(fn=os.path.join(path, 'project.xml'), **config.Projects)
    log.info("== BUILD PROJECT == %s" % os.path.basename(project.dirpath()))
    if format is None or 'epub' in format:
        project.build_epub(show_nav=True, 
            quality=config.EPUB.image_quality or 70, maxwh=config.EPUB.image_maxwh or 1024)
    if format is None or 'mobi' in format:
        project.build_mobi(
            quality=config.EPUB.image_quality or 70, maxwh=config.EPUB.image_maxwh or 1024)

def cleanup_project(path):
    ebooks_path = os.path.join(path, 'ebooks')
    dirs = [d for d in glob(ebooks_path+'/*') if os.path.isdir(d)]
    for d in dirs:
        log.debug("Removing: %s" % d)
        shutil.rmtree(d)

def zip_project(path):
    from bl.zip import ZIP
    return ZIP.zip_path(path)

def remove_project(path):
    shutil.rmtree(path)

if __name__=='__main__':
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.WARN)
    if len(sys.argv) < 2:
        log.warn("Usage: bg.project command project_filename ...")
    else:
        for path in sys.argv[2:]:
            path = os.path.abspath(path)
            if 'create' in sys.argv[1]:
                create_project(path)
            if 'import' in sys.argv[1]:
                import_all(path)
            if 'build' in sys.argv[1]:
                if '-epub' in sys.argv[1]: format='epub'
                elif '-mobi' in sys.argv[1]: format='mobi'
                else: format = None
                build_project(path, format=format)
            if 'cleanup' in sys.argv[1]:
                cleanup_project(path)
            if 'zip' in sys.argv[1]:
                zip_project(path)
            if 'remove' in sys.argv[1]:
                remove_project(path)
