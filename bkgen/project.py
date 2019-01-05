"""
The Project object is used to represent a project.xml file. Example usage:

>>> from bkgen.project import Project
>>> fn = '/path/to/Project-Folder/project.xml'
>>> project = Project(fn=fn)

Now all of the methods of the project can be called.
"""

import logging
log = logging.getLogger(__name__)

import json, os, re, shutil, subprocess, sys, tempfile, time, traceback, datetime
from copy import deepcopy
from glob import glob
from bl.dict import Dict
from bl.file import File
from bl.string import String
from bl.rglob import rglob
from bl.text import Text
from bl.dict import Dict
from bl.url import URL
from bl.zip import ZIP
from bgs.gs import GS
from bxml.xml import XML, etree
from bxml.xslt import XSLT # side-effect: registers lowercase and uppercase xpath functions
from bxml.builder import Builder

from bkgen import NS, config, mimetypes, PATH
from bkgen.document import Document
from bkgen.html import HTML
from bkgen.source import Source
from bkgen.css import CSS

PUB = Builder.single(NS.pub)
H = Builder.single(NS.html)

class Project(XML, Source):
    """Every project has a project.xml file that holds information about the project.
    The root element is pub:project, where ``pub:`` is the Publishing XML namespace 
    (see `publishingxml.org <http://publishingxml.org>`_).
    """
    NS = Dict(**{
        k:v for k,v in NS.items() 
        if k not in [                       # omit several sets of namespaces:
            'aid', 'aid5',                  # InDesign AID
            'cp', 'm', 'db',                # Microsoft, MathML, Docbook
        ]
    })
    ROOT_TAG = "{%(pub)s}project" % NS                                      #: The tag for the root element of a project.
    DEFAULT_NS = NS.pub

    # the kinds of inputs that are currently supported
    ACCEPTED_EXTENSIONS = [
        '.docx', '.htm', '.html', '.xhtml', '.md', '.txt',
        '.icml', '.idml', '.epub',
        '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']

    # the kinds of outputs that are currently supported
    OUTPUT_KIND_EXTS = Dict(**{
        'EPUB': '.epub', 
        'Kindle': '.mobi', 
        'HTML': '.zip'
    })

    @property
    def OUTPUT_EXT_KINDS(self): 
        return Dict(**{v:k for k,v in self.OUTPUT_KIND_EXTS.items()})

    def __init__(self, **args):
        XML.__init__(self, **args)
        if self.content_folder is None: self.content_folder = 'content'
        if self.image_folder is None: self.image_folder = self.content_folder + '/images'
        if self.cover_folder is None: self.cover_folder = 'cover'
        if self.output_folder is None: self.output_folder = 'outputs'
        if self.interior_folder is None: self.interior_folder = 'interior'
        if self.source_folder is None: self.source_folder = 'sources'

    def __repr__(self):
        return "Project(fn=%r)" % self.fn

    @property
    def name(self): 
        return self.root.get('name')

    @property
    def path(self):
        return os.path.dirname(os.path.abspath(self.fn))

    @property
    def content_path(self):
        path = os.path.join(self.path, self.content_folder)
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def image_path(self):
        path = os.path.join(self.path, str(self.image_folder))
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def cover_path(self):
        path = os.path.join(self.path, self.cover_folder)
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def output_path(self):
        path = os.path.join(self.path, str(self.output_folder))
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def interior_path(self):
        path = os.path.join(self.path, self.interior_folder)
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def source_path(self):
        path = os.path.join(self.path, self.source_folder)
        if not os.path.exists(path): os.makedirs(path)
        return path

    @property
    def output_kinds(self):
        return self.get('output_kinds') or self.OUTPUT_KIND_EXTS

    @property
    def title_text(self):
        return self.metadata().title.text or ''

    @property
    def cover_href(self):
        return self.find(self.root, "pub:resources/pub:resource[contains(@class,'cover') and @href]/@href")

    def spine_items(self):
        """Returns a list of items in the spine"""
        return self.root.xpath("pub:spine/pub:spineitem", namespaces=NS)

    def content_sections(self, include_content=True):
        """Returns a list of content sections that are available in this project.
        Potentially time-consuming to go through all the content.
        """
        data = []
        fns = rglob(os.path.join(self.path, self.content_folder), '*.xml')
        for fn in fns:
            x = XML(fn=fn)
            if x.root.tag != "{%(pub)s}document" % NS: continue
            for elem in x.root.xpath("//html:body/html:section[@id]", namespaces=NS):
                sd = Dict(
                    href=os.path.relpath(fn, self.path)+'#'+elem.get('id'),
                    title=elem.get('title'))
                if include_content==True:
                    sd.element = elem
                data.append(sd)
        return data

    # SOURCE METHODS
    def metadata(self):
        """metadata is kept in the project.xml opf:metadata block."""
        from .metadata import Metadata
        return Metadata(root=self.find(self.root, "opf:metadata", namespaces=NS))

    def resources(self):
        return self.find(self.root, "pub:resources", namespaces=NS)

    def documents(self):
        """all of pub:document files in the content subfolder."""
        from .document import Document
        return [Document(fn=fn) for fn in rglob(self.content_path, '*.xml')]

    def images(self):
        """all of the image files in the content subfolder."""
        from bf.image import Image
        images = [Image(fn=fn) 
            for fn 
            in rglob(os.path.join(self.path, self.content_folder), '*.*')
            if os.path.splitext(fn)[-1].lower() in 
                ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.pdf', '.bmp']
        ]
        return images

    def stylesheet(self):
        """the master .css for this project is the resource class="stylesheet"."""
        csshref = self.find(self.root, "pub:resources/pub:resource[@class='stylesheet']/@href", 
            namespaces=NS)
        if csshref is None:
            css = CSS(fn=os.path.join(PATH, 'templates', 'project.css'))
            css.fn = str(self.folder / 'project.css')
            css.write()
            csshref = css.relpath(self.path)
            resources = self.find(self.root, "pub:resources", namespaces=NS)
            css_resource = PUB.resource({'class': 'stylesheet', 'href': csshref})
            css_resource.tail = '\n\t\t'
            resources.append(css_resource)
        else:
            css = CSS(fn=str(self.folder / csshref))
        return css

    def content_stylesheet(self, href=None, fn=None):
        """If href is not None and the target document has an associated stylesheet, 
            combine the document stylesheet with the project stylesheet(s) to provide a single stylesheet,
            giving precedence to the project stylesheet(s). 
            (Precedence to the project stylesheet(s) allows the content stylesheet to be auto-generated, 
            and then for its styles to be pulled into the project stylesheet and edited there. Then when
            the content stylesheet is re-generated, the edits to those styles are not lost.)
        """
        css = self.stylesheet()
        log.debug("href = %r" % href)
        if href is not None:
            docfn = os.path.join(self.content_path, href.split('#')[0])
            doc_cssfn = os.path.splitext(docfn)[0] + '.css'
            log.debug("doc_cssfn = %r" % doc_cssfn)
            if os.path.exists(doc_cssfn):
                css = CSS.merge_stylesheets(css.fn, doc_cssfn)
        if fn is not None: css.fn = fn
        return css

    def files(self, depth=None, hidden=False):
        return [
            f for f in File(fn=self.path).file_list(depth=depth)
            if (hidden==True or os.path.basename(f.fn)[0]!='.')
        ]

    def content_files(self):
        """Return a list of files in the content folder"""
        return [
            f for f in File(fn=self.content_path).file_list()
            if os.path.basename(f.fn)[0]!='.'
        ]

    def source_files(self):
        """Return a list of files in the source folder"""
        return [
            f for f in File(fn=self.source_path).file_list()
            if os.path.basename(f.fn)[0]!='.'
        ]

    def output_files(self):
        return [
            f for f in File(fn=self.output_path).file_list()
            if os.path.basename(f.fn)[0]!='.'
        ]

    # CLASSMETHODS

    @classmethod
    def create(Class, parent_path, title, name=None, path=None, basename='project', refresh=False,
        include_stylesheet=True, **project_params):
        """create a new project.
            parent_path = the filesystem path to the parent folder that this project is in
            title = the title for the project
            name = the name of the project, which becomes its folder name and URL slug
            refresh=False: if True, delete any existing project file rather than loading it.
            project_params = parameters passed to the Project.__init__()
        
        Returns the Project XML object.
        """
        name = name or String(title).nameify()
        if not(re.match(r"^[\w\-\_\.]+$", name or '', flags=re.U)): 
            raise ValueError('Please provide a project name containing letters, numbers, hyphens, '
                + 'underscores, and periods -- no whitespace or special characters.')
        if not os.path.exists(parent_path):
            os.makedirs(parent_path)
            # raise ValueError("Before creating the project, first create the parent folder, %s" % parent_path)

        project_path = path or os.path.join(parent_path, name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        else:
            log.debug("Project folder already exists: %s" % project_path)

        project_fn = os.path.join(project_path, '%s.xml' % basename)
        if os.path.exists(project_fn) and refresh==True:
            log.info("Refreshing project by removing existing project file: %s" % project_fn)
            os.remove(project_fn)
        if os.path.exists(project_fn):
            log.debug("Project file already exists: %s" % project_fn)
            project = Class(fn=project_fn, **project_params)
        else:        
            project = Class(fn=os.path.join(PATH, 'templates', 'project.xml'), **project_params)
            project.fn = project_fn
            project.root.set('name', name)

        # update the title from what is given
        project.find(project.root, "opf:metadata/dc:title", namespaces=NS).text = title

        # make sure there is a base set of project folders
        for folder in [project.get(k) for k in project.keys() if '_folder' in k and project.get(k) is not None]:
            path = os.path.join(project_path, folder)
            if not os.path.exists(path): os.makedirs(path)

        # make sure there is a global content stylesheet for this project
        stylesheet_fn = None
        stylesheet_elem = project.find(project.root, 
            "pub:resources/pub:resource[@class='stylesheet']", namespaces=NS)
        if stylesheet_elem is not None:
            stylesheet_fn = os.path.abspath(os.path.join(project.path, str(URL(stylesheet_elem.get('href')))))
            if not os.path.exists(stylesheet_fn):
                stylesheet_elem.getparent().remove(stylesheet_elem)
                stylesheet_elem = None
        if stylesheet_elem is None and include_stylesheet==True:
            stylesheet_fn = os.path.splitext(project_fn)[0]+'.css'
            stylesheet_href = os.path.relpath(stylesheet_fn, project.path).replace('\\','/')
            project.add_resource(stylesheet_href, 'stylesheet')
            if not os.path.exists(stylesheet_fn):
                log.debug("stylesheet does not exist, creating")
                from bl.text import Text
                stylesheet = Text(fn=os.path.join(PATH, 'templates', 'project.css'))
                stylesheet.fn = stylesheet_fn
                stylesheet.write()
        log.debug("project stylesheet = %r" % stylesheet_fn)

        project.write()
        return project

    def add_resource(self, href, resource_class, kind=None):
        """add the given resource to the project file, if it isn't already present"""
        resources = self.resources()
        resource = self.find(resources, "/pub:resource[@href='%s' and @class='%s']" % (href, resource_class), namespaces=NS)
        if resource is None:
            resource = PUB.resource({'href':href, 'class':resource_class}); resource.tail='\n\t\t'
            if kind is not None: resource.set('kind', kind)
            resources.append(resource)
        else:
            log.warn("resource with that href already exists: %r" % resource.attrib)
        return resource

    def import_source_file(self, fn, SourceClass=None, **args):
        """import the source fn. 
        fn = the filesystem path to the file (such as a temporary file location)
        args = arguments that will be passed to Project.import_source()
        """
        content_type = mimetypes.guess_type(fn)[0]
        ext = os.path.splitext(fn)[-1].lower()
        result = Dict(fns=[])

        log.info("import %s" % fn)
        log.debug("%r.import_source_file(%r, **%r)" % (self, fn, args))
        
        # SourceClass is given
        if SourceClass is not None:
            result.fns += self.import_source(SourceClass(fn=fn), **args)

        # .DOCX files
        elif (content_type=='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                or ext=='.docx'):
            # write the content data to a temporary folder
            from .docx import DOCX
            result.fns += self.import_source(DOCX(fn=fn), **args)

        # .HTML files
        elif (content_type in ['text/html', 'application/xhtml+xml']
                or ext in ['.htm', '.html', '.xhtml']):
            # write the content data to a temporary folder
            from .html import HTML
            result.fns += self.import_source(HTML(fn=fn), **args)

        # .MD files
        elif (content_type=='text/x-markdown'
                or ext in ['.md', '.txt']):
            # write the content data to a temporary folder
            from .markdown import Markdown
            result.fns += self.import_source(Markdown(fn=fn), **args)

        # .EPUB files
        elif (content_type=='application/epub+zip'
                or ext == '.epub'):
            from .epub import EPUB
            result.fns += self.import_source(EPUB(fn=fn), **args)

        # .IDML files
        elif (content_type=='application/vnd.adobe.indesign-idml-package'
                or ext == '.idml'):
            from .idml import IDML
            result.fns += self.import_source(IDML(fn=fn), **args)

        # .XML files
        elif (content_type=='application/xml'
                and ext == '.icml'): 
            from .icml import ICML
            result.fns += self.import_source(ICML(fn=fn), **args)

        elif (content_type=='application/xml'
                and ext == '.xml'): 
            from .document import Document
            with open(fn, 'rb') as f:
                t = f.read()
                log.debug("importing Document: %r" % t)
            result.fns += self.import_source(Document(fn=fn), **args)

        # Images
        elif (content_type in ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff', 'application/pdf']
                or ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.pdf']):
            result.fns += self.import_image(fn, gs=config.Lib and config.Lib.gs or None)

        # not a matching file type
        else:
            result.message = 'Sorry, not a supported file type: %r (%r)' % (ext, content_type)
            result.status = 'error'
            log.error(result.message)

        if result.status is None:
            result.status = 'success'
            result.message = 'import succeeded.'

        return result
    
    def import_source(self, source, documents=True, images=True, stylesheet=True, metadata=False, 
        document_before_update_project=None, copy_to_source_folder=False, **params):
        """import a source into the project.
            source = a Source object that contains the content source [REQUIRED]
            documents = whether to import documents from the source (default=True)
            images = whether to import images from the source (default=True)
            stylesheet = whether to import a stylesheet from the source (default=True)
            metadata = whether to import metadata from the source (default=False)
            **params = passed to the Source.documents(**params) method
        """
        # If the source file is not already in the project folder and copy_to_source_folder is True, 
        # copy the source file into the "canonical" source file location for this project.
        # (if it's already in the project folder, don't copy or move it! Just use it where it is.)
        common_prefix = os.path.commonprefix([self.path, source.fn])
        log.debug("\n\tproject_path=%r\n\tsource.fn=%r\n\tcommon_prefix=%r\n\tproject path in common prefix? %r" 
            % (self.path, source.fn, common_prefix, self.path in common_prefix))
        if self.path not in common_prefix and copy_to_source_folder is True:
            fn = os.path.join(self.source_path, os.path.basename(source.fn))
            shutil.copy(source.fn, fn)
            source.fn = fn

        # import the documents, metadata, images, and stylesheet from this source
        fns = []
        if images==True: 
            imgfns = self.import_images(source.images())
            fns += imgfns
        if documents==True: 
            docs = source.documents(path=self.content_path, **params)
            docfns = self.import_documents(docs, source_path=source.path, 
                document_before_update_project=document_before_update_project)
            fns += docfns
        if metadata==True: 
            self.import_metadata(source.metadata())
        if stylesheet==True:
            ss = source.stylesheet()
            if ss is not None:
                # merge the stylesheet into the project.css
                css = self.stylesheet()
                with tempfile.NamedTemporaryFile() as tf:
                    ss.fn = tf.name
                    tf.close()
                    ss.write()
                    CSS.merge_stylesheets(css.fn, ss.fn).write()
        self.write()
        return fns

    def import_documents(self, documents, source_path=None, document_before_update_project=None):
        """import the given document collection. This includes 
        (1) storing the document in the project.content_folder 
        (2) adding sections of the document to the spine, if not present
        (3) importing referenced images, if available
        """
        with open(os.path.join(PATH, 'resources', 'epubtypes.json'), 'rb') as f:
            epubtypes = json.loads(f.read().decode('utf-8'))
        if documents is None: return
        spine_elem = self.find(self.root, "pub:spine")
        if spine_elem is None:
            log.debug('there is no spine element, add one')
            spine_elem = PUB.spine('\n\t\t')
            spine_elem.tail='\n\n\t'
            self.root.append(spine_elem)
        spine_elem.text = '\n\t\t'
        spine_hrefs = [
            str(URL(spineitem.get('href')))
            for spineitem in self.xpath(spine_elem, "pub:spineitem", namespaces=NS)
        ]
        fns = []
        for doc in documents:
            # save the document, overwriting any existing document in that location
            if (
                doc.fn is None 
                or self.content_path not in os.path.commonprefix([self.content_path, doc.fn])
            ):
                doc.fn = os.path.join(self.content_path, self.make_basename(doc.fn))

            # import referenced images, and update the image locations.
            if source_path is not None:
                for img in doc.root.xpath("//html:img[@src]", namespaces=NS):
                    srcfn = os.path.join(source_path, str(URL(img.get('src'))))
                    log.debug("img srcfn=%r exists? %r" % (srcfn, os.path.exists(srcfn)))
                    imgfn = os.path.join(self.image_path, self.make_basename(srcfn))
                    if os.path.exists(srcfn) and imgfn != srcfn:
                        if not os.path.exists(os.path.dirname(imgfn)):
                            os.makedirs(os.path.dirname(imgfn))
                        if os.path.exists(imgfn):
                            os.remove(imgfn)
                        shutil.copy(srcfn, imgfn)
                    img.set('src', File(imgfn).relpath(doc.path))
            doc.write(canonicalized=True)
            fns.append(doc.fn)

            if document_before_update_project is not None:
                document_before_update_project(doc)

            doc_href = doc.relpath(self.path)

            # remove missing content from spine
            doc_spine_hrefs = [href for href in spine_hrefs if '#' in href and href.split('#')[0]==doc_href]
            for href in doc_spine_hrefs:
                id = href.split('#')[-1]
                section = doc.find(doc.root, "//html:section[@id='%s']" % id, namespaces=NS)
                if section is None:
                    spineitem = self.find(spine_elem, "pub:spineitem[@href='%s']" % href)
                    log.info('Removing non-existent content from spine: %r' % spineitem.attrib)
                    spine_elem.remove(spineitem)

            # update the project spine: append anything that is new.
            sections = doc.root.xpath("html:body/html:section[@id]", namespaces=NS)
            for section in sections:
                section_href = doc_href + '#' + section.get('id')
                if section_href not in spine_hrefs:
                    spineitem = PUB.spineitem(href=section_href); spineitem.tail = '\n\t\t'
                    if section.get('title') is not None:
                        title = section.get('title')
                        spineitem.set('title', title)
                        for epubtype in epubtypes:
                            if re.search(epubtype['pattern'], title, flags=re.I) is not None:
                                spineitem.set('landmark', epubtype['type'])
                                break
                    spine_elem.append(spineitem)

        return fns

    def import_metadata(self, new_metadata):
        """import the metadata found in the Metadata XML object"""
        project_metadata = self.metadata()
        if new_metadata is None: return
        for elem in new_metadata.getchildren():
            # replace old_elem if it exists
            old_elem = self.find(project_metadata.root, 
                "*[@id='%s' or @property='%s']" % (elem.get('id'), elem.get('property')))
            if old_elem is not None:
                project_metadata.root.replace(old_elem, elem)
            else:
                project_metadata.root.append(elem)

            # make sure the element has an id
            if elem.get('id') is None:
                ns = project_metadata.tag_namespace(elem.tag)
                if ns in NS.values():
                    prefix = NS.keys()[NS.values().index(ns)]
                    tag = elem.tag.replace("{%s}" % ns, prefix+':')
                else:
                    tag = elem.tag
                elems = self.xpath(new_metadata, tag, namespaces=NS)
                id = tag.split(':')[-1]+str(len(elems)+1)
                elem.set('id', id)

    def import_images(self, images):
        if images is None: return
        fns = []
        for image in images:
            fns += [self.import_image(image.fn, gs=config.Lib and config.Lib.gs or None)]
        return fns

    def import_image(self, fn, gs=None, allpages=True, **params):
        """import the image from a local file. Process through GraphicsMagick to ensure clean."""
        # import the image to the project image folder
        from bf.image import Image
        if gs in params:
            gs = params.pop('gs')
        basename = self.make_basename(fn, ext='.jpg')
        if params.get('class') is not None and 'cover' in params.get('class'):
            outfn = os.path.join(self.path, str(self.cover_folder), basename)
        else:
            outfn = os.path.join(self.path, str(self.image_folder), basename)
        log.debug('image: %s' % os.path.relpath(fn, self.path).replace('\\','/'))
        ext = os.path.splitext(fn)[-1].lower()
        if ext in ['.pdf', '.eps']:
            gso = GS(gs=gs)
            gso.render(fn, outfn, device='jpeg', res=600, allpages=allpages)
        else:
            Image(fn=fn).convert(outfn, format='jpg', quality=100)

        # create / update the resource for the image
        image_file = File(fn=outfn)
        log.debug("resource = %s" % image_file.relpath(self.path))
        href = image_file.relpath(self.path)
        resource = self.find(self.root, "//pub:resource[@href='%s']" % href, namespaces=NS)
        if resource is None:
            resource = etree.Element("{%(pub)s}resource" % NS, href=href, **params)
            resource.tail = '\n\t'
        
        resources = self.find(self.root, "pub:resources")

        if 'cover' in (resource.get('class') or ''):
            if ((params.get('kind') is None or 'digital' in params.get('kind'))):
                existing_cover_digital = self.find(self.root, 
                    "//pub:resource[contains(@class,'cover') and (@kind='%s' or not(@kind))]" 
                    % params.get('kind') or 'digital', namespaces=NS)
                if existing_cover_digital is not None:
                    resources.remove(existing_cover_digital)
                    log.debug("removing existing cover: %r" % existing_cover_digital.attrib)

        resources.append(resource)
        log.debug("appending resource: %r" % resource.attrib)

        self.write()
        return outfn

    def get_cover_href(self, kind='digital'):
        return self.find(self.root, """
            pub:resources/pub:resource[contains(@class, 'cover') and 
                (not(@kind) or contains(@kind, '%s'))]/@href""" % kind, namespaces=NS)        

    def build_outputs(self, kind=None, output_kinds=[], cleanup=False, before_compile=None, 
        doc_stylesheets=True, singlepage=False):
        """build the project outputs
            kind=None:      which kind of output to build; if None, build all
        """
        log.info("build_outputs: %s %r" % (self.fn, dict(kind=kind, cleanup=cleanup, before_compile=before_compile, doc_stylesheets=doc_stylesheets, singlepage=singlepage)))
        if kind is not None:
            output_kinds = [kind]
        elif output_kinds==[]:
            output_kinds = self.OUTPUT_KIND_EXTS.keys()
        results = []

        for output_kind in output_kinds:
            log.info("output kind=%r" % output_kind)
            try:
                start_time = time.time()
                assert output_kind in self.OUTPUT_KIND_EXTS.keys()
                if output_kind=='EPUB':
                    result = self.build_epub(cleanup=cleanup, doc_stylesheets=doc_stylesheets, 
                        before_compile=before_compile)
                elif output_kind=='Kindle':
                    result = self.build_mobi(cleanup=cleanup, doc_stylesheets=doc_stylesheets, 
                        before_compile=before_compile)
                elif output_kind=='HTML':
                    result = self.build_html(cleanup=cleanup, doc_stylesheets=doc_stylesheets, 
                        singlepage=singlepage)
                elif output_kind=='Archive':
                    result = self.build_archive()
                result.size = File(fn=result.fn).size
                result.status = 'completed'
            except:
                msg = (str(String(sys.exc_info()[0].__name__).camelsplit()) + ' ' + str(sys.exc_info()[1])).strip()
                result = Dict(kind=output_kind, status='error', message=msg, traceback=traceback.format_exc())
                log.error(result.traceback)
            finally:
                result.time = time.time() - start_time
                result.kind = output_kind
            
            results.append(result)

        return results

    def build_archive(self):
        """create a zip archive of the project folder itself"""
        outfn = os.path.join(self.path, str(self.output_folder), self.name+'.zip')
        zipfn = ZIP.zip_path(self.path, fn=outfn, mode='w',
            exclude=[os.path.relpath(outfn, self.path).replace('\\','/')])            # avoid recursive self-inclusion
        result = Dict(fn=zipfn, format="pub")
        return result

    def build_epub(self, clean=True, show_nav=False, doc_stylesheets=True, progress=None, name_kind=True,
            zip=True, check=True, cleanup=False, before_compile=None, lang=None, **image_args):
        from .epub import EPUB
        epub_isbn = self.metadata().identifier(id_patterns=['epub', 'ebook', 'isbn'])
        
        if epub_isbn is not None and epub_isbn.text is not None:
            epub_name = str(String(epub_isbn.text)
                # remove any dashes or whitespace
                .resub(r'[\s\-\u058a\u2011\u2012\u2013\u2014\u2015\ufe58\ufe63\uff0d]', ''))
        else:
            epub_name = self.name
        epub_path = os.path.join(self.path, str(self.output_folder), epub_name+'_EPUB')
        if name_kind==True:
            epub_name += '_EPUB'
        
        if clean==True: 
            if os.path.isdir(epub_path):
                shutil.rmtree(epub_path, onerror=rmtree_warn)

        if not os.path.isdir(epub_path): os.makedirs(epub_path)
        resources = self.output_resources(output_path=epub_path, **image_args)
        if progress is not None: progress.report()
        metadata = self.find(self.root, "opf:metadata", namespaces=NS)
        cover_src = self.get_cover_href(kind='digital')
        if lang is None: 
            dclang = self.find(metadata,'dc:language')
            if dclang is not None:
                lang = dclang.text
            else:
                lang = 'en'
        spine_items = self.output_spineitems(output_path=epub_path, resources=resources, 
            ext='.xhtml', doc_stylesheets=doc_stylesheets, lang=lang, 
            conditions='digital epub', **image_args)
        if progress is not None: progress.report()
        result = EPUB().build(epub_path, metadata, progress=progress, lang=lang,
            epub_name=epub_name, spine_items=spine_items, cover_src=cover_src, 
            show_nav=show_nav, before_compile=before_compile, zip=zip, check=check)
        if cleanup==True: 
            shutil.rmtree(epub_path, onerror=rmtree_warn)
        return result

    def build_html(self, clean=True, singlepage=False, ext='.xhtml', doc_stylesheets=True, progress=None,
            before_compile=None, zip=True, cleanup=False, lang=None, **image_args):
        """build html output of the project. 
        * singlepage=False  : whether to build the HTML in a single page
        * zip=True          : whether to zip the output
        * cleanup=False     : whether to cleanup the output folder (only if zip=True)
        """
        from .epub import EPUB
        log.debug("build_html: %r" % dict(clean=clean, singlepage=singlepage, ext=ext, doc_stylesheets=doc_stylesheets, zip=zip, cleanup=cleanup, **image_args))
        html_path = os.path.join(self.output_path, self.name+'_HTML')
        log.info(html_path)
        if clean==True and os.path.isdir(html_path): 
            shutil.rmtree(html_path, onerror=rmtree_warn)
        if not os.path.isdir(html_path): 
            os.makedirs(html_path)
        result = Dict(format="html", reports=[])
        resources = self.output_resources(output_path=html_path, **image_args)
        if progress is not None: progress.report()
        if lang is None: 
            dclang = self.find(self.root,'opf:metadata/dc:language')
            if dclang is not None:
                lang = dclang.text
            else:
                lang = 'en'
        spine_items = self.output_spineitems(output_path=html_path, resources=resources, 
            ext=ext, singlepage=singlepage, doc_stylesheets=doc_stylesheets, lang=lang, 
            conditions='digital html', **image_args)
        if singlepage != True:
            EPUB.make_nav(html_path, spine_items, show_nav=True, nav_href="index.xhtml")
        if before_compile is not None:
            before_compile(html_path)
        if zip==True:
            from bl.zip import ZIP
            result['fn'] = ZIP.zip_path(html_path)
            if cleanup==True: 
                shutil.rmtree(html_path, onerror=rmtree_warn)
        else:
            result['fn'] = html_path
        if progress is not None: progress.report()
        return result

    def build_mobi(self, clean=True, cleanup=False, before_compile=None, progress=None, name_kind=True,
            doc_stylesheets=True, lang=None, **image_args):
        from .mobi import MOBI
        mobi_isbn = self.metadata().identifier(id_patterns=['mobi', 'ebook', 'isbn'])
        if mobi_isbn is not None and mobi_isbn.text is not None:
            mobi_name = str(String(mobi_isbn.text)
                # remove any dashes or whitespace
                .resub(r'[\s\-\u058a\u2011\u2012\u2013\u2014\u2015\ufe58\ufe63\uff0d]', ''))
        else:
            mobi_name = self.name
        mobi_path = os.path.join(self.path, str(self.output_folder), mobi_name+'_Kindle')
        if name_kind==True:
            mobi_name += '_Kindle'

        if clean==True and os.path.isdir(mobi_path): 
            shutil.rmtree(mobi_path, onerror=rmtree_warn)

        if not os.path.isdir(mobi_path): os.makedirs(mobi_path)
        resources = self.output_resources(output_path=mobi_path, **image_args)
        if progress is not None: progress.report()
        metadata = self.root.find("{%(opf)s}metadata" % NS)
        cover_src = self.get_cover_href(kind='digital')
        if lang is None: 
            dclang = self.find(metadata,'dc:language')
            if dclang is not None:
                lang = dclang.text
            else:
                lang = 'en'
        spine_items = self.output_spineitems(output_path=mobi_path, resources=resources, 
            ext='.html', http_equiv_content_type=True, doc_stylesheets=doc_stylesheets, lang=lang, 
            conditions='digital mobi', **image_args)
        if progress is not None: progress.report()
        result = MOBI().build(mobi_path, metadata, lang=lang,
                mobi_name=mobi_name, spine_items=spine_items, cover_src=cover_src, before_compile=before_compile)
        if cleanup==True: 
            shutil.rmtree(mobi_path, onerror=rmtree_warn)
        if progress is not None: progress.report()
        return result

    def output_resources(self, output_path=None, **image_args):
        log.debug("project.output_resources()")
        output_path = output_path or os.path.join(self.path, str(self.output_folder))
        resources = [deepcopy(resource) 
                    for resource 
                    in self.root.xpath("pub:resources/pub:resource[not(@include='False')]", namespaces=NS)]
        for resource in resources:
            log.debug(resource.attrib)
            f = File(fn=os.path.abspath(os.path.join(self.path, str(URL(resource.get('href'))))))
            if resource.get('class')=='stylesheet':
                outfn = self.output_stylesheet(f.fn, output_path)
            elif resource.get('class') in ['cover', 'cover-digital', 'image']:
                outfn = self.output_image(f.fn, output_path=output_path, gs=config.Lib and config.Lib.gs or None, **image_args)
            else:                                                               # other resource as-is
                outfn = os.path.join(output_path, f.relpath(os.path.dirname(self.fn)))
                f.write(fn=outfn)
            resource.set('href', File(fn=outfn).relpath(output_path))
        return resources

    def output_stylesheet(self, fn, output_path=None):
        output_path = output_path or os.path.join(self.path, str(self.output_folder))
        outfn = os.path.join(output_path, os.path.relpath(fn, self.path).replace('\\','/'))
        log.debug("project.output_stylesheet(): %r" % outfn)
        if os.path.splitext(fn)[-1] == '.scss':
            from bf.scss import SCSS
            outfn = os.path.splitext(outfn)[0]+'.css'
            SCSS(fn=fn).render_css().write(fn=outfn)
        else:
            Text(fn=fn).write(fn=outfn)
        return outfn

    def output_image(self, fn, output_path=None, outfn=None, jpg=True, png=True, svg=True, gs=None, 
            format='jpeg', ext='.jpg', res=300, quality=90, maxwh=None, maxpixels=4e6, **img_args):
        from bf.image import Image
        f = File(fn=fn)
        mimetype = mimetypes.guess_type(fn)
        log.debug("srcfn: %s %r %r" % (fn, mimetype, os.path.exists(fn)))
        if 'gs' in img_args:
            gs = img_args.pop('gs')
        output_path = output_path or os.path.join(self.path, str(self.output_folder))
        outfn = outfn or os.path.splitext(os.path.join(output_path, f.relpath(self.path)))[0] + ext
        log.debug("outfn: %s" % outfn)

        # try writing the image multiple times (at most 5) to ensure clean output
        image_data_tries = []
        i = 0
        while i < 5:
            i += 1
            try:
                if not os.path.exists(os.path.dirname(outfn)):
                    os.makedirs(os.path.dirname(outfn))
                
                if mimetype=='application/pdf' or f.ext.lower() == '.pdf':
                    from bf.pdf import PDF
                    PDF(fn=fn).gswrite(fn=outfn, device=format, res=res, gs=gs)
                elif (mimetype=='image/jpeg' or f.ext=='.jpg') and jpg==True:
                    outfn = os.path.splitext(outfn)[0] + '.jpg'
                    f.write(fn=outfn)
                elif (mimetype=='image/png' or f.ext=='.png') and png==True:
                    outfn = os.path.splitext(outfn)[0] + '.png'
                    f.write(fn=outfn)
                elif (mimetype=='image/svg+xml' or f.ext=='.svg') and svg==True:
                    outfn = os.path.splitext(outfn)[0] + '.svg'
                    f.write(fn=outfn)
                elif format in mimetype or f.ext == ext:
                    f.write(fn=outfn)
                elif f.ext != '.svg':
                    Image(fn=fn).convert(outfn)

                # make sure the output image fits the parameters
                log.debug("%s %r" % (outfn, os.path.exists(outfn)))
                image = Image(fn=outfn)

                img_args.update(density="%dx%d" % (res,res))
                if os.path.splitext(outfn)[-1].lower()=='.jpg':
                    img_args.update(quality=quality)

                if os.path.splitext(outfn)[-1].lower() != '.svg':
                    width, height = [int(i) for i in image.identify(format="%w,%h").split(',')]
                    if ((maxpixels is not None and (width * height) > maxpixels) 
                        or (maxwh is not None and (width > maxwh or height > maxwh))
                    ):
                        if maxpixels is not None and width * height > maxpixels:  # reduce dimension to fit maxpixels
                            fraction = (maxpixels / (width * height)) ** 0.5
                            width *= fraction
                            height *= fraction
                        if maxwh is not None and width > maxwh:               # reduce dimensions to fit maxwh
                            height *= maxwh / width
                            width = maxwh
                        if maxwh is not None and height > maxwh:
                            width *= maxwh / height
                            height = maxwh
                        width, height = int(width), int(height)

                        log.debug("res=%r, width=%r, height=%r" % (res, width, height))
                        img_args.update(geometry="%dx%d>" % (width, height))

                    # apply the img_args to the image -- only once, so that we don't lose quality in jpeg output
                    image.mogrify(**img_args)
                    log.debug("img: %r %r" % (outfn, img_args))

                # here we compare the image_data from this write to what was done previously
                image_data = open(outfn, 'rb').read()
                if image_data in image_data_tries: 
                    break
                image_data_tries.append(image_data)
                if len(image_data_tries) > 2:
                    log.info("try %d for %s" % (len(image_data_tries)+1, outfn))
                if len(image_data_tries)>=5:
                    log.warn("continuing with inconsistent image results for %s" % outfn)
                    break
            except KeyboardInterrupt:
                raise
            except:
                # the show must go on
                log.critical(fn)
                log.critical(traceback.format_exc())

        return outfn

    def output_spineitems(self, output_path=None, ext='.xhtml', resources=None, singlepage=False,
            http_equiv_content_type=False, doc_stylesheets=True, lang='en', 
            conditions='digital', **image_args):
        from bf.image import Image
        from .document import Document
        log.debug("project.output_spineitems()")
        output_path = output_path or os.path.join(self.path, str(self.output_folder))
        if resources is None: 
            resources = self.output_resources(output_path=output_path, **image_args)
        spineitems = [deepcopy(spineitem) for spineitem in 
                    self.root.xpath("pub:spine/pub:spineitem[not(@include='False')]", namespaces=NS)]
        outfns = []
        css_fns = glob(os.path.join(self.content_path, '*.css'))
        endnotes = []                   # collect endnotes and pass into and out of Document.html()
        for spineitem in spineitems:
            split_href = str(URL(spineitem.get('href'))).split('#')
            log.debug(split_href)
            docfn = os.path.join(self.path, split_href[0])
            if os.path.dirname(docfn) == self.content_path:
                doc_css_fns = glob(os.path.splitext(docfn)[0]+'.css')
            else:
                doc_css_fns = glob(os.path.dirname(docfn)+'.css')
            if len(split_href) > 1: 
                d = Document.load(fn=docfn, id=split_href[1])
            else:
                d = Document.load(fn=docfn)
            outfn = os.path.splitext(os.path.join(output_path, os.path.relpath(d.fn, self.path).replace('\\','/')))[0] + ext
            if 'html' in ext:
                # create the output html for this document
                h = d.html(fn=outfn, ext=ext, output_path=output_path, http_equiv_content_type=http_equiv_content_type,
                    resources=resources, endnotes=endnotes, lang=lang, conditions=conditions)
                # add the document-specific CSS, if it exists
                if len(doc_css_fns) > 0 and doc_stylesheets==True:
                    css_fns = []
                    head = h.find(h.root, "html:head", namespaces=NS)
                    for css_link in h.xpath(head, "html:link[@rel='stylesheet' and @href]", namespaces=NS):
                        css_fns.append(os.path.abspath(os.path.join(h.path, str(URL(css_link.get('href'))))))
                        head.remove(css_link)    # we won't need the project stylesheets separately, because we're merging
                    for doc_css_fn in doc_css_fns:
                        out_css_fn = os.path.splitext(
                            os.path.join(output_path, os.path.relpath(doc_css_fn, self.path).replace('\\','/'))
                            )[0]+'.css'
                        if not os.path.exists(out_css_fn):
                            merge_css_fns = css_fns + [doc_css_fn]
                            out_css = CSS.merge_stylesheets(merge_css_fns[0], *merge_css_fns[1:])
                            out_css.fn = out_css_fn
                            out_css.write()
                        log.debug("doc_css: %r" % out_css_fn)
                        href = os.path.relpath(out_css_fn, h.dirpath()).replace('\\','/')
                        link = etree.Element("{%(html)s}link" % NS, rel="stylesheet", href=href, type="text/css")
                        head.append(link)

                # output any images that are referenced from the document and are locally available
                for img in h.root.xpath("//html:img", namespaces=NS):
                    srcfn = os.path.join(d.path, str(URL(img.get('src'))))
                    if os.path.exists(srcfn):
                        args = dict(**image_args)
                        outfn = self.output_image(srcfn, output_path=output_path, gs=config.Lib and config.Lib.gs or None, **args)
                        img.set('src', os.path.relpath(outfn, h.path).replace('\\','/'))
                    else:
                        log.error("IMAGE NOT FOUND: %s" % srcfn)
                        # h.remove(img, leave_tail=True)

                h.write(doctype="<!DOCTYPE html>", canonicalized=False)
                outfns.append(h.fn)
                spineitem.set('href', os.path.relpath(h.fn, output_path).replace('\\','/'))

        project_css_fn = os.path.join(output_path, self.find(self.root, "pub:resources/pub:resource[@class='stylesheet']/@href", namespaces=NS) or 'project.css')

        if len(endnotes) > 0:           # create a new spineitem for the endnotes, and put them there
            enfn = os.path.join(output_path, self.content_folder, 'Collected-Endnotes'+ext)
            endnotes_html = Document().html(fn=enfn, output_path=output_path)
            if os.path.exists(project_css_fn):
                head = endnotes_html.find(endnotes_html.root, "html:head", namespaces=NS)
                head.append(
                    H.link(rel="stylesheet", type="text/css", 
                        href=os.path.relpath(project_css_fn, endnotes_html.path).replace('\\','/')))
            body = endnotes_html.find(endnotes_html.root, "//html:body")
            if body is None:
                body = H.body('\n'); body.tail = '\n'
                endnotes_html.root.append(body)
            section = H.section('\n', {'class': 'endnotes', 'id':'Collected-Endnotes'})
            body.append(section)
            while len(endnotes) > 0:
                endnote = endnotes.pop(0)
                endnote.tail = '\n'
                section.append(endnote)
            endnotes_html.write(canonicalized=False)
            endnotes_spineitem = PUB.spineitem(
                href= os.path.relpath(endnotes_html.fn, output_path).replace('\\','/'),
                title="Endnotes")
            spineitems.append(endnotes_spineitem)
            outfns.append(endnotes_html.fn)

        if singlepage==True and len(spineitems) > 0:
            # concatenate all the outfns into a single document
            from .html import HTML
            html = HTML()
            html.root.set('lang', lang)
            html.root.set('{%(xml)s}lang'%NS, lang)
            html.fn = os.path.join(output_path, self.content_folder, self.name + ext)
            title = self.metadata().title.text if self.metadata().title is not None else ''
            spineitems = [PUB.spineitem(href=os.path.relpath(html.fn, output_path).replace('\\','/'), title=title)]
            # head = H.head(
            #         H.title(title),
            #         H.meta({'charset': 'UTF-8'}))
            # for stylesheet in self.xpath(self.root, "pub:resources/pub:resource[@class='stylesheet']"):
            #     link = H.link(rel='stylesheet', type='text/css',
            #         href=os.path.relpath(
            #             os.path.abspath(os.path.join(self.path, stylesheet.get('href'))),
            #             html.path)).replace('\\','/')
            html.root.append(
                H.head(
                    H.title(title),
                    H.meta({'charset': 'UTF-8'}),
                    H.link(rel="stylesheet", type="text/css", 
                        href=os.path.relpath(project_css_fn, html.path).replace('\\','/'))))
            body = H.body('\n')
            html.root.append(body)
            html.write()
            for outfn in outfns:
                h = HTML(fn=outfn)
                for elem in h.xpath(h.root, "html:body/*"):
                    body.append(elem)
                try:
                    os.remove(h.fn)
                except:
                    log.error("FILE NOT FOUND: %r" % h.fn)
            outfns = [html.fn]
            html.write()

        # FIXME: This assumes that id attributes are unique across the product.
        # We cannot assume this.
        if 'html' in ext:
            # collect the @ids from the content and fix the hyperlinks
            basenames = [self.make_basename(f) for f in outfns]
            ids = Dict()
            for outfn in outfns:
                for elem in XML(fn=outfn).root.xpath("//*[@id]"):
                    ids[elem.get('id')] = outfn

            # relink to the correct items
            for outfn in outfns:
                log.debug(outfn)
                x = XML(fn=outfn)
                for e in [
                    e for e in x.root.xpath("//html:a[@href]", namespaces=NS) 
                    if len(e.get('href')) > 0 and (
                        e.get('href')[0]=='#'
                        or e.get('href').split('#')[0] not in basenames)
                ]:
                    hreflist = str(URL(e.get('href'))).split('#')
                    if len(hreflist) > 1:      # we have an id -- use it to resolve the link
                        id = hreflist[1]
                        if id in ids:
                            rp = os.path.relpath(ids[id], x.path).replace('\\','/')
                            if rp == x.basename:        # location in the same file, omit filename
                                rp = ''
                            e.set('href', rp+'#'+id)
                    else:               # only a filename
                        outfb = os.path.splitext(
                            os.path.abspath(
                                os.path.join(
                                    os.path.dirname(outfn), hreflist[0])))[0]
                        for hfn in outfns:
                            if outfb in hfn:
                                e.set('href', os.path.relpath(hfn, os.path.dirname(outfn)).replace('\\','/'))
                                break
                    e.set('href', URL(e.get('href')).quoted())      # urls need to be quoted.

                x.write(canonicalized=False)

        # only keep the first instance of a given pagebreak in the outputs
        pagebreak_ids = []
        for outfn in outfns:
            x = XML(fn=outfn)
            for pagebreak in x.xpath(x.root, "//html:span[@id and (@epub:type='pagebreak' or @role='doc-pagebreak')]", namespaces=NS):
                if pagebreak.get('id') in pagebreak_ids:
                    x.remove(pagebreak, leave_tail=True)
                else:
                    pagebreak_ids.append(pagebreak.get('id'))
            x.write(canonicalized=False)

        return spineitems

    def cleanup(self, resources=False, outputs=False, logs=False, exclude=None):
        """clean up the project:
        outputs=True:   remove all folders from the output folder
        resources=True: remove all non-referenced resources (non-xml) from the content folder
        exclude=None:   regexp pattern to exclude from cleanup
        """
        log.debug("cleanup %s: %r" % (self.name, {'resources':resources, 'outputs':outputs, 'logs':logs, 'exclude':exclude}))
        if outputs==True:
            dirs = [
                d for d in glob(self.output_path+'/*') 
                if os.path.isdir(d)
                and (exclude is None or re.search(exclude, d) is None)
            ]
            log.info("cleanup: removing %d output directories from %s" % (len(dirs), self.path))
            for d in dirs:
                log.debug("removing: %s" % d)
                shutil.rmtree(d, onerror=rmtree_warn)
        if logs==True:
            log_glob = os.path.join(self.path, '/logs', '*.log')
            log.debug("cleanup logs: %s" % log_glob)
            for fn in glob(log_glob):
                os.remove(fn)
        if resources==True:
            # Get all the resource filenames that don't match the exclusion pattern
            resourcefns = list(set([
                File(fn=fn).splitext()[0] 
                for fn in rglob(self.content_path, "*.*") 
                if os.path.splitext(fn)[-1].lower()!='.xml'
                and (exclude is None or re.search(exclude, fn) is None)
            ]))
            log.debug('%d content resources' % len(resourcefns))
            # pop from the list those that are referenced from the content
            xmlfns = [self.fn] + rglob(self.content_path,'*.xml')
            for xmlfn in xmlfns:
                x = XML(fn=xmlfn)
                hreffns = list(set([
                    File(fn=os.path.abspath(os.path.join(x.path, href.split('#')[0]))).splitext()[0]
                    for href in Document.xpath(x.root, "//@href|//@src|//@altimg")
                ]))
                log.debug('%d hrefs in %s' % (len(hreffns), x.fn))
                for hreffn in hreffns:
                    if hreffn in resourcefns:
                        log.debug('retain: %s' % hreffn)
                        resourcefns.pop(resourcefns.index(hreffn))
            log.info('cleanup: removing %d orphaned content resources from %s' % (len(resourcefns), self.path))
            # delete those that remain -- not excluded, not referenced
            for resourcefn in resourcefns:
                fns = glob(resourcefn+'.*')
                for fn in fns:
                    os.remove(fn)

    def delete(self):
        """delete the project and all it contains"""
        log.info("project.delete(): %r" % self.path)
        if os.path.isdir(self.path):
            shutil.rmtree(self.path)

    def delete_file(self, filepath):
        log.info("project.delete_file(%r)" % filepath)
        if os.path.exists(filepath):
            fn = filepath
        elif os.path.exists(os.path.join(self.path, filepath)):
            fn = os.path.abspath(os.path.join(self.path, filepath))
        if os.path.isdir(fn):
            shutil.rmtree(fn)
            log.info("removed directory: %s" % fn)
        elif os.path.isfile(fn):
            os.remove(fn)
            log.info("removed file: %s" % fn)
        href = File.normpath(os.path.relpath(fn, self.path))
        for e in self.xpath(self.root, "//*[@href]"):
            if e.get('href').startswith(href):
                self.remove(e)
        self.write()

    def delete_content_item(self, fn, id=None):
        log.info("fn   = %s (%r)" % (fn, os.path.exists(fn)))
        href = os.path.relpath(fn, self.path)
        if id is not None:
            href += '#' + id
        if os.path.exists(fn):
            if id is None:
                os.remove(fn)
            else:
                doc = Document(fn=fn)
                section = doc.find(doc.root, "//*[@id='%s']" % id)
                if section is not None:
                    doc.remove(section, leave_tail=True)
                    doc.write()
            for spineitem in self.xpath(self.root, "//pub:spineitem[contains(@href,'%s')]" % href):
                self.remove(spineitem)
            self.write()


def rmtree_warn(function, path, excinfo):
    log.warn("%s: Could not remove %s: %s" % (function.__name__, path, excinfo()[1]))

# == COMMAND INTERFACE METHODS == 

def import_all(project_path):
    """import sources, cover, and metadata into project"""
    project = Project(fn=os.path.join(project_path, 'project.xml'), **(config.Project or {}))
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
    fns = rglob(interior_path, '*.idml') + rglob(source_path, '*.idml')
    log.info('-- %d .idml files' % len(fns))
    for fn in fns:
        project.import_source_file(fn, fns=fns)
    
    # import icml 
    fns = rglob(interior_path, '*.icml') + rglob(source_path, '*.icml')
    log.info('-- %d .icml files' % len(fns))
    for fn in fns: 
        project.import_source_file(fn, fns=fns)
    
    # import docx
    fns = rglob(interior_path, '*.docx') + rglob(source_path, '*.docx')
    log.info('-- %d .docx files' % len(fns))
    for fn in fns:
        project.import_source_file(fn, fns=fns, with_metadata=False)

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
        project.import_image(fn, gs=config.Lib and config.Lib.gs or None)
    
    # cover
    fns = rglob(cover_path, "*.jpg")
    for fn in fns:
        project.import_image(fn, gs=config.Lib and config.Lib.gs or None, **{'class':'cover', 'kind':'digital'})

def build_project(project_path, format=None, check=None, doc_stylesheets=True, singlepage=False, before_compile=None):
    if os.path.isfile(project_path):
        project_fn = project_path
    elif os.path.isdir(project_path) and os.path.isfile(os.path.join(project_path, 'project.xml')):
        project_fn = os.path.join(project_path, 'project.xml')
    else:
        log.error("Project not found: %s" % project_path)
        return
    project = Project(fn=project_fn, **(config.Project or {}))
    log.debug("== BUILD PROJECT == %s" % os.path.basename(os.path.dirname(project.fn)))

    # default formats
    if format is None or 'epub' in format:
        image_args = config.EPUB.images or {}
        project.build_epub(check=check, before_compile=before_compile, **image_args)
    if format is None or 'mobi' in format:
        image_args = config.Kindle.images or {}
        project.build_mobi(before_compile=before_compile, **image_args)

    # non-default formats
    if format is not None:
        if 'html' in format:
            image_args = config.EPUB.images or {}
            project.build_html(singlepage=singlepage, before_compile=before_compile, **image_args)
        if 'archive' in format:
            project.build_archive()

def cleanup_project(project_path, outputs=False, resources=False, logs=False, exclude=None):
    project = Project(fn=os.path.join(project_path, 'project.xml'), **(config.Project or {}))
    project.cleanup(outputs=outputs, resources=resources, logs=logs, exclude=exclude)

def zip_project(project_path):
    from bl.zip import ZIP
    return ZIP.zip_path(project_path)

def remove_project(project_path):
    shutil.rmtree(project_path, onerror=rmtree_warn)

if __name__=='__main__':
    from bkgen import config
    logging.basicConfig(**config.Logging)
    if len(sys.argv) < 2:
        log.warn("Usage: python -m bkgen.project command project_path [project_path] ...")
    else:
        project_path = File(os.path.abspath(sys.argv[2])).fn    # normalize by all means!
        fns = [File(fn=fn).fn for fn in sys.argv[3:]]
        if os.path.isdir(project_path):
            project_fn = os.path.join(project_path, 'project.xml')
        elif project_path[-len('project.xml'):]=='project.xml':
            project_fn = project_path
            project_path = os.path.dirname(project_path)
        else:
            # in this case, we probably have a file under the project path.
            fns = [project_path] + fns
            path_elems = project_path.split('/')
            while len(path_elems) > 0:
                project_fn = '/'.join(path_elems + ['project.xml'])
                if os.path.exists(project_fn):
                    log.info(project_fn)
                    break
                path_elems.pop(-1)
        project = Project(fn=project_fn)

        if 'create' in sys.argv[1]:
            Project.create(os.path.dirname(project_path), os.path.basename(project_path), path=project_path)
        
        if 'import-all' in sys.argv[1]:
            import_all(project_path)
        elif 'import-cover' in sys.argv[1]:
            project.import_image(fns[0], gs=config.Lib and config.Lib.gs or None, **{'class':'cover'})
        elif 'import' in sys.argv[1]:
            project = Project(fn=project_fn)
            for fn in fns:
                project.import_source_file(fn, fns=fns)

        if 'stylesheet' in sys.argv[1]:
            css = project.stylesheet()
            css.write()
            css = CSS.merge_stylesheets(css.fn, *fns)
            css.write()
        
        if 'build' in sys.argv[1]:
            if sys.argv[1]=='build': 
                project.build_outputs()
            if '-epub' in sys.argv[1]: 
                project.build_outputs(kind='EPUB')
            if '-mobi' in sys.argv[1]: 
                project.build_outputs(kind='Kindle')
            if '-html' in sys.argv[1]:
                project.build_outputs(kind='HTML', singlepage='-single' in sys.argv[1])
            if '-archive' in sys.argv[1]: 
                project.build_outputs(kind='archive')
        if 'clean' in sys.argv[1]:
            cleanup_project(project_path, outputs='outputs' in sys.argv[1], resources='resources' in sys.argv[1])
        if 'zip' in sys.argv[1]:
            zip_project(project_path)
        if 'remove' in sys.argv[1]:
            remove_project(project_path)
