import logging, os
from lxml import etree
from bl.dict import Dict
from bl.file import File
from bl.folder import Folder
from bl.id import random_id
from bl.string import String
from bl.url import URL
from bl.zip import ZIP
from bxml import XML
from bxml.builder import Builder
from .icml import ICML
from bkgen.document import Document
from bkgen import NS
from bkgen.source import Source

LOG = logging.getLogger(__name__)
B = Builder(default=NS.html, **{'html': NS.html, 'pub': NS.pub})


class IDML(ZIP, Source):
    NS = ICML.NS

    @property
    def basename(self):
        return os.path.splitext(os.path.basename(self.fn))[0]

    @property
    def output_path(self):  # a directory next to the .idml file with the same basename
        return os.path.splitext(self.fn)[0]

    @property
    def designmap(self):
        """The designmap.xml contains the definitions for Hyperlinks, Destinations, Bookmarks, and the like,
        so it's needed to resolve links within an IDML file as well as between IDML files in a collection.
        """
        if self.__designmap is None:
            self.__designmap = ICML(root=self.read('designmap.xml'))
        return self.__designmap

    @property
    def stories(self):
        """it's useful to have access to all the stories (as ICML documents) in the package. Cached, as with others."""
        if self.__stories is None:
            self.__stories = []
            for story in self.designmap.root.xpath("idPkg:Story", namespaces=self.NS):
                fn = os.path.join(self.splitext()[0], os.path.basename(str(URL(story.get('src')))))
                icml = ICML(fn=fn, root=self.read(story.get('src')))
                self.__stories.append(icml)
        return self.__stories

    @property
    def items(self):
        """returns a dict of items (anything with a Self) in the IDML file. Needed to resolve Article components."""
        if self.__items is None:
            d = Dict()
            for rp in [
                rp for rp in self.zipfile.namelist() if os.path.splitext(rp)[-1].lower() == '.xml'
            ]:
                x = XML(root=self.read(rp))
                for item in x.root.xpath("//*[@Self] | //idPkg:*[@Self]", namespaces=self.NS):
                    if item.get('Self') in d and d[item.get('Self')].attrib != item.attrib:
                        LOG.error(
                            "%s already in items_dict. %r vs. %r"
                            % (item.get('Self'), d[item.get('Self')].attrib, item.attrib)
                        )
                    else:
                        d[item.get('Self')] = item
            self.__items = d
        return self.__items

    def styles(self):
        return ICML(root=self.read('Resources/Styles.xml')).styles()

    def stylesheet(self, fn=None):
        """return a stylesheet from the .idml file's style definitions"""
        if fn is None:
            fn = os.path.join(self.output_path, os.path.basename(self.output_path) + '.css')
        return ICML(root=self.read('Resources/Styles.xml')).stylesheet(fn=fn)

    def document(self, path=None, articles=True, sources=None, **params):
        """return a pub:document with the articles / stories in the .idml file.
        path=None: The path in which the document files are created.
        articles=True: If the .idml file has Articles, use those as guidance; 
            otherwise, use the stories directly.
        sources=None: The collection of source documents
            (e.g., to resolve hyperlinks in a multi-publication InDesign book).
        """
        path = path or self.output_path
        if sources is None:
            sources = [self]
            for fn in [fn for fn in (params.get('fns') or []) if fn != self.fn]:
                sources.append(IDML(fn=fn))
        # Articles or Stories?
        if articles == True and len(self.designmap.root.xpath("//Article")) > 0:
            doc = self.articles_document(path=path, sources=sources)
        else:
            doc = self.stories_document(path=path, sources=sources)
        return doc

    def articles_document(self, path=None, sources=None):
        """return a collection of pub:documents built from the InDesign Articles in the .idml file.
        """
        path = path or self.output_path
        sources = sources or [self]
        doc = Document()
        doc.fn = str(Folder(path) / (os.path.splitext(self.basename)[0] + '.xml'))
        doc_body = doc.find(doc.root, "html:body")
        for article in self.designmap.root.xpath("//Article"):
            article_icml = ICML()
            article_icml.fn = os.path.splitext(doc.fn)[0] + '.icml'
            LOG.debug("article name=%r icml.fn = %r" % (article.get('Name'), article_icml.fn))
            for member in article.xpath("ArticleMember"):
                item = self.items[member.get('ItemRef')]
                LOG.debug(
                    "ItemRef=%r => %r ParentStory=%r"
                    % (member.get('ItemRef'), item.tag, item.get('ParentStory'))
                )
                for elem in item.xpath("descendant-or-self::*[@ParentStory]"):
                    story_id = elem.get('ParentStory')
                    pkg_story = self.designmap.find(
                        self.designmap.root,
                        "//idPkg:Story[contains(@src, '%s')]" % story_id,
                        namespaces=ICML.NS,
                    )
                    # Add the story to the Article document as a section
                    story_icml = ICML(root=self.read(str(URL(pkg_story.get('src')))))
                    for story in story_icml.root.xpath("//Story"):
                        article_icml.root.append(story)

            article_doc = article_icml.document(
                srcfn=self.fn, sources=sources, styles=self.styles()
            )
            for incl in article_doc.xpath(article_doc.root, "//pub:include[@idref]", namespaces=NS):
                parent = incl.getparent()
                incl_pkg = self.designmap.root.find(
                    "idPkg:Story[@src='Stories/Story_%s.xml']" % incl.get('idref'),
                    namespaces=self.NS,
                )
                if incl_pkg is not None:
                    incl_doc = ICML(root=self.read(str(URL(incl_pkg.get('src'))))).document(
                        fn=self.fn, srcfn=self.fn, sources=sources, styles=self.styles()
                    )
                    for ch in incl_doc.find(
                        incl_doc.root, "html:body", namespaces=NS
                    ).getchildren():
                        parent.insert(parent.index(incl), ch)
                    parent.remove(incl)

            for elem in article_doc.xpath(article_doc.root, "html:body/*", namespaces=NS):
                doc_body.append(elem)

        return doc

    def stories_document(self, path=None, sources=None):
        path = path or self.output_path
        sources = sources or [self]
        doc = Document()
        doc.fn = str(Folder(path) / (os.path.splitext(self.basename)[0] + '.xml'))
        doc_body = doc.find(doc.root, "html:body")
        doc_body.text = '\n'
        icml_fn = os.path.splitext(doc.fn)[0] + '.icml'
        for story in self.designmap.root.xpath("idPkg:Story", namespaces=self.NS):
            icml = ICML(fn=icml_fn, root=self.read(str(URL(story.get('src')))))
            idoc = icml.document(srcfn=self.fn, sources=sources, styles=self.styles())
            for elem in idoc.xpath(idoc.root, "html:body/*", namespaces=NS):
                doc_body.append(elem)
        return doc
