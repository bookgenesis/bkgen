
import logging
log = logging.getLogger(__name__)

import os, re, shutil, subprocess, sys, time, traceback
from copy import deepcopy
from bl.file import File
from bl.string import String
from bl.rglob import rglob
from bl.text import Text
from bl.dict import Dict
from bl.zip import ZIP
from bxml.xml import XML, etree
from bxml.builder import Builder

from bkgen import NS

FILENAME = os.path.abspath(__file__)
PATH = os.path.dirname(FILENAME)
PUB = Builder.single(NS.pub)

class Project(XML):
    """Every project has a project.xml file that holds information about the project.
    The root element is pub:project, where 'pub:' is the Publishing XML namespace (see http://publishingxml.org).
    """
    ROOT_TAG = "{%(pub)s}project" % NS
    OUTPUT_KINDS = {'EPUB':'.epub', 'Kindle':'.mobi', 'Archive':'.zip'}

    def __init__(self, **args):
        XML.__init__(self, **args)
        if self.content_folder is None: self.content_folder = 'content'
        if self.image_folder is None: self.image_folder = self.content_folder + '/images'
        if self.cover_folder is None: self.cover_folder = 'cover'
        if self.output_folder is None: self.output_folder = 'outputs'
        if self.interior_folder is None: self.interior_folder = 'interior'
        if self.source_folder is None: self.source_folder = 'sources'

    @property
    def name(self): 
        return self.root.get('name')

    @property
    def metadata(self):
        """metadata is kept in the project.xml opf:metadata block."""
        from .metadata import Metadata
        return Metadata(root=self.find(self.root, "opf:metadata", namespaces=NS))

    @property
    def path(self):
        return os.path.dirname(os.path.abspath(self.fn))

    @classmethod
    def create(Class, parent_path, title, name=None, **project_params):
        """create a new project.
            parent_path = the filesystem path to the parent folder that this project is in
            title = the title for the project
            name = the name of the project, which becomes its folder name and URL slug
            **project_params = parameters passed to the Project.__init__()
        Returns the Project XML object.
        """
        name = name or String(title).nameify()
        if not(re.match(r"^[\w\-\_\.]+$", name or '', flags=re.U)): 
            raise ValueError('Please provide a project name containing letters, numbers, hyphens, undescores, and periods -- no whitespace or special characters.')
        if not os.path.exists(parent_path):
            raise ValueError("Before creating the project, first create the parent folder, %s" % parent_path)

        project_path = os.path.join(parent_path, name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        else:
            log.info("Project folder already exists: %s" % project_path)

        project_fn = os.path.join(project_path, 'project.xml')
        if os.path.exists(project_fn):
            log.info("Project file already exists, not overwriting: %s" % project_fn)
            project = Class(fn=project_fn, **project_params)
        else:        
            project = Class(fn=os.path.join(PATH, 'templates', 'project.xml'), **project_params)
            project.fn = os.path.join(project_path,'project.xml')
            project.root.set('name', name)
            project.find(project.root, "opf:metadata/dc:title", namespaces=NS).text = title

        # make sure there is a base set of project folders
        for folder in [project.get(k) for k in project.keys() if '_folder' in k and project.get(k) is not None]:
            path = os.path.join(project_path, folder)
            if not os.path.exists(path): os.makedirs(path)

        # make sure there is a global content stylesheet for this project
        stylesheet_fn = os.path.join(project.path, 'project.css')
        log.debug("project stylesheet = %r" % stylesheet_fn)
        if not os.path.exists(stylesheet_fn):
            log.debug("stylesheet does not exist, creating")
            from bl.text import Text
            stylesheet = Text(fn=os.path.join(PATH, 'templates', 'project.css'))
            stylesheet.fn = stylesheet_fn
            stylesheet.write()

        # make sure the global stylesheet is reflected in the resources
        stylesheet_elem = project.find(project.root, 
            "pub:resources/pub:resource[@class='stylesheet']", namespaces=NS)
        if stylesheet_elem is None:
            stylesheet_href = os.path.relpath(stylesheet_fn, project.path)
            project.add_resource(stylesheet_href, 'stylesheet')

        project.write()
        return project

    def add_resource(self, href, rclass, kind=None):
        """add the given resource to the project file, if it isn't already present"""
        resources = self.find(self.root, "pub:resources", namespaces=NS)
        resource = self.find(resources, "/pub:resource[@href='%s' and @class='%s']" % (href, rclass), namespaces=NS)
        if resource is None:
            resource = PUB.resource({'href':href, 'class':rclass}); resource.tail='\n\t\t'
            if kind is not None: resource.set('kind', kind)
            resources.append(resource)
        else:
            raise ValueError("resource with that href already exists: %r" % resource.attrib)
        return resource

    def import_source(self, source, documents=True, images=True, stylesheet=True, metadata=False):
        """import a source into the project.
            source : an object that contains the content source; must have the following interface:
                source.fn               -- the current full filename of the source
                source.write(fn=...)    -- to write the content source to the given filename
                source.documents()      -- to return a collection of <pub:document/> containing the content (or [])
                source.images()         -- to return a collection of Image files from the source (or [])
                source.metadata()       -- to return a Metadata XML object containing source metadata (or None)
                source.stylesheet()     -- to return a CSS stylesheet from this source (or None)
        """
        # move / copy the source into the "canonical" source file location for this project.
        source_new_fn = os.path.join(self.path, self.source_folder, self.make_basename(fn=source.fn))
        if source_new_fn != source.fn:
            if self.path in os.path.commonprefix([self.fn, source.fn]):
                os.rename(source.fn, source_new_fn)
            else:
                shutil.copy(source.fn, source_new_fn)
            source.fn = source_new_fn

        # import the documents, metadata, images, and stylesheet from this source
        if documents==True: self.import_documents(source.documents())
        if metadata==True: self.import_metadata(source.metadata())
        if images==True: self.import_images(source.images())
        if stylesheet==True:
            ss = source.stylesheet()
            if ss is not None:
                ss.fn = os.path.join(self.path, self.content_folder, self.make_basename(fn=source.fn, ext='.css'))
                ss.write()

        self.write()

    def import_documents(self, documents):
        """import the given document collection. This includes 
        (1) storing the document in the project.content_folder 
        (2) adding sections of the document to the spine, if not present
        """
        if documents is None: return
        spine_elem = self.find(self.root, "pub:spine", namespaces=NS)
        spine_hrefs = [spineitem.get('href') 
            for spineitem in self.find(spine_elem, "pub:spineitem", namespaces=NS)]
        for doc in documents:
            # save the document, overwriting any existing document in that location
            doc.fn = os.path.join(self.path, self.content_folder, self.make_basename(fn=doc.fn))
            doc.write()

            # update the project spine element: append anything that is new.
            sections = doc.root.xpath("html:body/html:section[@id]", namespaces=NS)
            for section in sections:
                section_href = os.path.relpath(doc.fn, self.path) + '#' + section.get('id')
                if section_href not in spine_hrefs:
                    spineitem = PUB.spineitem(href=section_href); spineitem.tail = '\n\t\t'
                    for attrib in ['title', 'epub:type']:
                        if section.get(attrib, namespaces=NS) is not None:
                            spineitem.set(attrib, section.get(attrib, namespaces=NS), namespaces=NS)
                    spine_elem.append(spineitem)

    def import_metadata(self, metadata):
        """import the metadata found in the Metadata XML object"""
        project_metadata = self.metadata.root
        if metadata is None: return
        for elem in metadata.root.getchildren():
            # replace old_elem if it exists
            old_elem = self.find(project_metadata, "*[@id='%s' or @property='%s']" % (elem.get('id'), elem.get('property')))
            if old_elem is not None:
                project_metadata.replace(old_elem, elem)
            else:
                project_metadata.append(elem)

            # make sure the element has an id
            if elem.get('id') is None:
                ns = metadata.tag_namespace(elem.tag)
                if ns in NS.values():
                    prefix = NS.keys()[NS.values().index(ns)]
                    tag = elem.tag.replace("{%s}" % ns, prefix+':')
                else:
                    tag = elem.tag
                elems = self.xpath(metadata, tag, namespaces=NS)
                id = tag.split(':')[-1]+str(len(elems)+1)
                elem.set('id', id)

    def import_images(self, images):
        if images is None: return
        for image in images:
            self.import_image(image.fn)

    def import_image(self, fn):
        """import the image from a local file. Process through GraphicsMagick to ensure clean."""
        basename = re.sub("(&[\w^;]+;|[\s\&+;'])", "-", os.path.basename(os.path.splitext(fn)[0]+'.jpg'))
        outfn = os.path.join(self.path, self.image_folder, basename)
        log.debug('image: %s' % os.path.relpath(fn, self.path))
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
        resource_fn = os.path.join(self.path, self.image_folder, basename)
        log.debug("resource = %s" % os.path.relpath(resource_fn, self.path))

        f.write(fn=resource_fn)
        log.debug(os.path.relpath(resource_fn, self.path))
        href = os.path.relpath(resource_fn, self.path)
        resource = self.find(self.root, "//pub:resource[@href='%s']" % href, namespaces=NS)
        if resource is None:
            resource = etree.Element("{%(pub)s}resource" % NS, **{'href':href, 'class':'image'})
            resource.tail = '\n\t'
            resources = self.find(self.root, "pub:resources", namespaces=NS)
            resources.append(resource)

        if params.get('class')=='cover-digital' and os.path.splitext(resource_fn)[-1]=='.jpg':
            existing_cover_digital = self.find(self.root, 
                "//pub:resource[@class='cover-digital']", namespaces=NS)
            if existing_cover_digital is not None:
                existing_cover_digital.set('class', 'image')
            resource.set('class', 'cover-digital')

        if db is not None:
           self.make_resource_excerpts(db, content_href=href)

        self.write()

    def get_cover_href(self, kind='digital'):
        return self.find(self.root, """
            pub:resources/pub:resource[contains(@class, 'cover') and 
                (not(@kind) or contains(@kind, '%s'))]/@href""" % kind, namespaces=NS)        

    def build_outputs(self, kind=None):
        """build the project outputs
            kind=None:      which kind of output to build; if None, build all
        """
        log.info("build project outputs: %s" % self.fn)
        output_kinds = [k for k in self.OUTPUT_KINDS.keys() if kind is None or k==kind]
        results = []
        for output_kind in output_kinds:
            try:
                log.info("output kind=%r" % output_kind)
                assert output_kind in self.OUTPUT_KINDS.keys()
                if output_kind=='EPUB':
                    result = self.build_epub()
                elif output_kind=='Kindle':
                    result = self.build_mobi()
                elif output_kind=='Archive':
                    result = self.build_archive_zip()
            except:
                msg = (str(String(sys.exc_info()[0].__name__).camelsplit()) + ' ' + str(sys.exc_info()[1])).strip()
                result = Dict(kind=output_kind, message=msg, traceback=traceback.format_exc())
                log.error(result.msg)
                log.debug(result.traceback)
            results.append(result)
        return results

    def build_archive_zip(self):
        """create a zip archive of the project folder itself"""
        outfn = os.path.join(self.path, self.output_folder, self.name+'.zip')
        zipfn = ZIP.zip_path(self.path, fn=outfn, mode='w',
            exclude=[os.path.relpath(outfn, self.path)])            # avoid recursive self-inclusion
        result = Dict(fn=zipfn)
        return result

    def build_epub(self, clean=True, show_nav=False, zip=True, check=True, cleanup=False, **image_args):
        from .epub import EPUB
        epub_isbn = self.metadata.get_dc_identifier(id_patterns=['epub', 'ebook', 'isbn'])
        if epub_isbn is not None and epub_isbn.text is not None:
            epub_name = epub_isbn.text.replace('-', '')
        else:
            epub_name = self.name
        epub_path = os.path.join(self.path, self.output_folder, epub_name+"_EPUB")
        if clean==True and os.path.isdir(epub_path): shutil.rmtree(epub_path)
        if not os.path.isdir(epub_path): os.makedirs(epub_path)
        resources = self.output_resources(output_path=epub_path, **image_args)
        metadata = self.find(self.root, "opf:metadata", namespaces=NS)
        cover_src = self.get_cover_href(get='digital')
        spine_items = self.output_spineitems(output_path=epub_path, resources=resources, 
            ext='.xhtml', **image_args)
        result = EPUB().build(epub_path, metadata, 
            epub_name=epub_name, spine_items=spine_items, cover_src=cover_src, 
            show_nav=show_nav, zip=zip, check=check)
        if cleanup==True: shutil.rmtree(epub_path)
        return result

    def build_mobi(self, clean=True, cleanup=False, **image_args):
        from .mobi import MOBI
        mobi_isbn = self.metadata.get_dc_identifier(id_patterns=['mobi', 'ebook', 'isbn'])
        if mobi_isbn is not None:
            mobi_name = mobi_isbn.text.replace('-', '')
        else:
            mobi_name = self.name
        mobi_path = os.path.join(self.path, self.output_folder, mobi_name+"_MOBI")
        if clean==True and os.path.isdir(mobi_path): shutil.rmtree(mobi_path)
        if not os.path.isdir(mobi_path): os.makedirs(mobi_path)
        resources = self.output_resources(output_path=mobi_path, **image_args)
        metadata = self.root.find("{%(opf)s}metadata" % NS)
        cover_src = self.get_cover_href(kind='digital')
        spine_items = self.output_spineitems(output_path=mobi_path, resources=resources, 
            ext='.html', http_equiv_content_type=True, canonicalized=False, **image_args)
        result = MOBI().build(mobi_path, metadata, 
                mobi_name=mobi_name, spine_items=spine_items, cover_src=cover_src)
        if cleanup==True: shutil.rmtree(mobi_path)
        return result

    def output_resources(self, output_path=None, **image_args):
        log.debug("project.output_resources()")
        output_path = output_path or os.path.join(self.path, self.output_folder)
        resources = [deepcopy(resource) 
                    for resource 
                    in self.root.xpath("pub:resources/pub:resource[not(@include='False')]", namespaces=NS)]
        for resource in resources:
            f = File(fn=os.path.abspath(os.path.join(self.path, resource.get('href'))))
            if resource.get('class')=='stylesheet':
                outfn = self.output_stylesheet(f.fn, output_path)
            elif resource.get('class') in ['cover', 'image']:
                outfn = self.output_image(f.fn, output_path, **image_args)
            else:                                                               # other resource as-is
                outfn = os.path.join(output_path, os.path.relpath(f.fn, os.path.dirname(self.fn)))
                f.write(fn=outfn)
            resource.set('href', os.path.relpath(outfn, output_path))
            log.debug(resource.attrib)
        return resources

    def output_stylesheet(self, fn, output_path=None):
        log.debug("project.output_stylesheet()")
        output_path = output_path or os.path.join(self.path, self.output_folder)
        outfn = os.path.join(output_path, os.path.relpath(fn, self.path))
        if os.path.splitext(fn)[-1] == '.scss':
            from bf.scss import SCSS
            outfn = os.path.splitext(outfn)[0]+'.css'
            SCSS(fn=fn).render_css().write(fn=outfn)
        else:
            File(fn=fn).write(fn=outfn)
        return outfn

    def output_image(self, fn, output_path=None, outfn=None, 
            format='jpeg', ext='.jpg', res=300, quality=80, maxwh=2048):
        f = File(fn=fn)
        mimetype = f.mimetype() or ''
        output_path = output_path or os.path.join(self.path, self.output_folder)
        outfn = outfn or os.path.splitext(os.path.join(output_path, f.relpath(dirpath=self.path)))[0] + ext
        if not os.path.exists(os.path.dirname(outfn)):
            os.makedirs(os.path.dirname(outfn))
        if mimetype=='application/pdf' or f.ext().lower() == '.pdf':
            from bf.pdf import PDF
            res = PDF(fn=fn).gswrite(fn=outfn, device=format, res=res)
        elif 'image/' in mimetype:
            from bf.image import Image
            img_args=Dict(
                format=format.upper(), 
                density="%dx%d" % (res,res),
                geometry="%dx%d>" % (maxwh, maxwh))
            if format.lower() in ['jpeg', 'jpg']:
                img_args.update(quality=quality)
            res = Image(fn=fn).convert(outfn, **img_args)
        else:
            res = None
        return outfn

    def output_spineitems(self, output_path=None, ext='.xhtml', resources=None, 
                http_equiv_content_type=False, canonicalized=False, **image_args):
        from bf.image import Image
        log.debug("project.output_spineitems()")
        output_path = output_path or os.path.join(self.path, self.output_folder)
        if resources is None: resources = self.output_resources(output_path=output_path, **image_args)
        spineitems = [deepcopy(spineitem) for spineitem in 
                    self.root.xpath("pub:spine/pub:spineitem[not(@include='False')]", namespaces=NS)]
        outfns = []
        for spineitem in spineitems:
            split_href = spineitem.get('href').split('#')
            docfn = os.path.join(self.path, split_href[0])
            if len(split_href) > 1: 
                d = Document.load(fn=docfn, section_id=split_href[1])
            else:
                d = Document.load(fn=docfn)
            outfn = os.path.splitext(os.path.join(output_path, os.path.relpath(d.fn, self.path)))[0] + ext
            if 'html' in ext:
                # create the output html for this document
                h = d.html(fn=outfn, ext=ext, resources=resources, 
                        output_path=output_path, http_equiv_content_type=http_equiv_content_type)
                # add the document-specific CSS, if it exists
                doc_css_fn = os.path.splitext(docfn)[0]+'.css'
                out_css_fn = os.path.splitext(
                    os.path.join(output_path, os.path.relpath(docfn, self.path)))[0]+'.css'
                if os.path.exists(doc_css_fn) and not os.path.exists(out_css_fn):
                    Text(fn=doc_css_fn).write(fn=out_css_fn)
                if os.path.exists(out_css_fn):
                    head = h.find(h.root, "html:head", namespaces=NS)
                    href = os.path.relpath(out_css_fn, h.dirpath())
                    link = etree.Element("{%(html)s}link" % NS, rel="stylesheet", href=href, type="text/css")
                    head.append(link)
                h.write(doctype="<!DOCTYPE html>", canonicalized=canonicalized)
                outfns.append(h.fn)
                spineitem.set('href', os.path.relpath(h.fn, output_path))

                # output any images that are referenced from the document and are locally available
                for img in h.root.xpath("//html:img", namespaces=NS):
                    srcfn = os.path.join(d.path, img.get('src'))
                    if os.path.exists(srcfn):
                        _ = self.output_image(srcfn, outfn=outfn, **image_args)
                    else:
                        log.warn("IMAGE NOT FOUND: %s" % srcfn)

        if 'html' in ext:
            # collect the @ids from the content and fix the hyperlinks
            basenames = [os.path.basename(f) for f in outfns]
            ids = Dict()
            for outfn in outfns:
                for elem in XML(fn=outfn).root.xpath("//*[@id]"):
                    ids[elem.get('id')] = outfn
            for outfn in outfns:
                x = XML(fn=outfn)
                for e in [
                        e for e in x.root.xpath("//*[contains(@href, '#')]") 
                        if (e.get('href')[0]=='#'
                            or e.get('href').split('#')[0] not in basenames)]:
                    id = e.get('href').split("#")[-1]
                    if id in ids:
                        e.set('href', os.path.relpath(ids[id], x.path)+'#'+id)
                # images will be jpegs
                for e in x.root.xpath("//html:img[@src]", namespaces=NS):
                    e.set('src', os.path.splitext(e.get('src'))[0]+'.jpg')
                x.write()

        return spineitems

# == COMMAND INTERFACE METHODS == 

def import_all(project_path, **config):
    """import sources, cover, and metadata into project"""
    project = Project(fn=os.path.join(project_path, 'project.xml'), **(config.get('Projects') or {}))
    basename = os.path.basename(project.path)
    log.info("== IMPORT ALL FOR PROJECT: %s ==" % basename)

    # make sure the project folders exist
    interior_path = os.path.join(project.path, project.interior_folder)
    if not os.path.exists(interior_path): os.makedirs(interior_path)
    source_path = os.path.join(project.path, project.source_folder)
    if not os.path.exists(source_path): os.makedirs(source_path)
    cover_path = os.path.join(project.path, project.cover_folder)
    if not os.path.exists(cover_path): os.makedirs(cover_path)
    
    # import idml if available
    log.info('-- %d .idml files' % len(fns))
    fns = rglob(interior_path, '*.idml') + rglob(source_path, '*.idml')
    for fn in fns:
        project.import_source(IDML(fn=fn), fns=fns)
    
    # import icml 
    fns = rglob(interior_path, '*.icml') + rglob(source_path, '*.icml')
    log.info('-- %d .icml files' % len(fns))
    for fn in fns: 
        project.import_source(ICML(fn=fn), fns=fns)
    
    # import docx
    fns = rglob(interior_path, '*.docx') + rglob(source_path, '*.docx')
    log.info('-- %d .docx files' % len(fns))
    for fn in fns:
        project.import_source(DOCX(fn=fn), with_metadata=False)

    # import metadata.xml
    fns = [fn for fn in rglob(project.path, '*metadata.xml')
            if '.itmsp' not in fn]      # not inside an iTunes Producer package
    log.info('-- %d metadata.xml files' % len(fns))            
    for fn in fns:
        project.import_metadata(fn)
    
    # images
    fns = [fn for fn in rglob(interior_path+'/Links', "*.*")
        if os.path.splitext(fn)[-1].lower() in ['.pdf', '.jpg', '.png', '.tif', '.tiff', '.eps']]
    log.info('-- %d image files' % len(fns))
    for fn in fns:
        project.import_image(fn)
    
    # cover
    fns = rglob(cover_path, "*.jpg")
    for fn in fns:
        project.import_image(fn, **{'class': 'digital'})

def build_project(project_path, format=None, **config):
    log.info("== BUILD PROJECT == %s" % os.path.basename(project_path))
    project = Project(fn=os.path.join(project_path, 'project.xml'), **(config.get('Projects') or {}))
    image_args = {k:c[k] for k in (config.EPUB or {}).keys() if 'image_' in k}
    if format is None or 'epub' in format:
        project.build_epub(show_nav=True, **image_args)
    if format is None or 'mobi' in format:
        project.build_mobi(**image_args)

def cleanup_project(project_path):
    project = Project(fn=os.path.join(project_path, 'project.xml'), **(config.get('Projects') or {}))
    ebooks_path = os.path.join(path, 'ebooks')
    dirs = [d for d in glob(ebooks_path+'/*') if os.path.isdir(d)]
    for d in dirs:
        log.debug("Removing: %s" % d)
        shutil.rmtree(d)

def zip_project(project_path):
    from bl.zip import ZIP
    return ZIP.zip_path(project_path)

def remove_project(project_path):
    shutil.rmtree(project_path)

if __name__=='__main__':
    from bkgen import config
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.WARN)
    if len(sys.argv) < 2:
        log.warn("Usage: python -m bkgen.project command project_path [project_path] ...")
    else:
        for project_path in sys.argv[2:]:
            project_path = os.path.abspath(project_path)
            if 'create' in sys.argv[1]:
                Project.create(os.path.dirname(project_path), os.path.basename(project_path), **config.Projects)
            if 'import' in sys.argv[1]:
                import_all(path, **config.Projects)
            if 'build' in sys.argv[1]:
                if '-epub' in sys.argv[1]: format='epub'
                elif '-mobi' in sys.argv[1]: format='mobi'
                else: format = None
                build_project(path, format=format)
            if 'cleanup' in sys.argv[1]:
                cleanup_project(project_path)
            if 'zip' in sys.argv[1]:
                zip_project(project_path)
            if 'remove' in sys.argv[1]:
                remove_project(project_path)
