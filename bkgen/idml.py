
import logging
log = logging.getLogger(__name__)

import os
from lxml import etree
from bl.dict import Dict
from bl.file import File
from bl.id import random_id
from bl.string import String
from bl.url import URL
from bl.zip import ZIP
from bxml import XML
from .icml import ICML
from bkgen import NS
from bkgen.source import Source

class IDML(ZIP, Source):
    NS = ICML.NS

    @property
    def basename(self):
        return os.path.splitext(os.path.basename(self.fn))[0]

    @property
    def output_path(self):                  # a directory next to the .idml file with the same basename
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
            for rp in [rp for rp in self.zipfile.namelist() if os.path.splitext(rp)[-1].lower()=='.xml']:
                x = XML(root=self.read(rp))
                for item in x.root.xpath("//*[@Self] | //idPkg:*[@Self]", namespaces=self.NS):
                    if item.get('Self') in d and d[item.get('Self')].attrib != item.attrib:
                        log.error("%s already in items_dict. %r vs. %r" % (item.get('Self'), d[item.get('Self')].attrib, item.attrib))
                    else:
                        d[item.get('Self')] = item
            self.__items = d
        return self.__items

    def documents(self, path=None, articles=True, sources=None, **params):
        """return a collection of pub:documents from the stories in the .idml file.
        path=None: The path in which the document files are created.
        articles=True: If the .idml file has Articles, use those as guidance; otherwise, use the stories directly.
        sources=None: The collection of other source documents to be treated as a collection with this one.
            (This is needed, for example, to resolve hyperlinks in a multi-publication InDesign book.)
        """
        path = path or self.output_path
        if sources is None:
            sources = [self]
            for fn in [fn for fn in (params.get('fns') or []) if fn != self.fn]:
                sources.append(IDML(fn=fn))
        documents = []
        if articles==True and len(self.designmap.root.xpath("//Article")) > 0:  # Articles?
            documents += self.articles_documents(path=path, sources=sources)
        else:                                                                   # or Stories?
            for story in self.designmap.root.xpath("idPkg:Story", namespaces=self.NS):
                outfn = os.path.join(path, self.clean_filename(self.basename), os.path.basename(str(URL(story.get('src')))))
                icml = ICML(fn=outfn, root=self.read(str(URL(story.get('src')))))
                document = icml.document(srcfn=self.fn, sources=sources, styles=self.styles())
                for incl in document.xpath(document.root, "//pub:include[@idref]", namespaces=NS):
                    incl_story = self.designmap.root.find("idPkg:Story[@src='Stories/Story_%s.xml']" % incl.get('idref'), namespaces=self.NS)
                    if incl_story is not None:
                        incl.set('src', URL(incl_story.get('src')).basename)
                document.write()
                documents.append(document)
        # fix links between documents
        ids = {}
        for d in documents:
            for e in d.root.xpath("//*[@id]"):
                ids[e.get('id')] = d.fn
        for doc in documents:
            for e in doc.root.xpath("//pub:include[@id]", namespaces=NS):
                if e.get('id') in ids:
                    id = e.attrib.pop('id')
                    targetfn = ids[id]
                    e.set('src', os.path.relpath(targetfn, os.path.dirname(doc.fn)) + '#' + id)
        return documents

    def articles_documents(self, path=None, sources=None):
        """return a collection of pub:documents built from the InDesign Articles in the .idml file.
        """
        from bxml.builder import Builder
        from bkgen.document import Document
        if sources is None: sources=[self]
        B = Builder(default=NS.html, **{'html':NS.html, 'pub':NS.pub})
        path = path or self.output_path
        documents = []
        output_path = self.clean_filename(os.path.join(path, self.basename))
        log.debug('output_path = %r' % output_path)
        for article in self.designmap.root.xpath("//Article"):
            article_icml = ICML()
            article_icml.fn = os.path.join(output_path+'-'+self.make_basename(article.get('Name'), ext='.icml'))
            log.debug("article name=%r icml.fn = %r" % (article.get('Name'), article_icml.fn))
            for member in article.xpath("ArticleMember"):
                item = self.items[member.get('ItemRef')]
                log.debug("ItemRef=%r => %r ParentStory=%r" % (member.get('ItemRef'), item.tag, item.get('ParentStory')))
                for elem in item.xpath("descendant-or-self::*[@ParentStory]"):
                    story_id = elem.get('ParentStory')
                    pkg_story = self.designmap.find(self.designmap.root, 
                        "//idPkg:Story[contains(@src, '%s')]" % story_id, namespaces=ICML.NS)

                    # Add the story to the Article document as a section
                    story_icml = ICML(root=self.read(str(URL(pkg_story.get('src')))))
                    for story in story_icml.root.xpath("//Story"): 
                        article_icml.root.append(story)
            document = article_icml.document(srcfn=self.fn, sources=sources, styles=self.styles())
            for incl in document.xpath(document.root, "//pub:include[@idref]", namespaces=NS):
                parent = incl.getparent()
                incl_pkg = self.designmap.root.find("idPkg:Story[@src='Stories/Story_%s.xml']" % incl.get('idref'), namespaces=self.NS)
                if incl_pkg is not None:
                    incl_doc = ICML(root=self.read(str(URL(incl_pkg.get('src'))))).document(fn=self.fn, srcfn=self.fn, sources=sources, styles=self.styles())
                    for ch in incl_doc.find(incl_doc.root, "html:body", namespaces=NS).getchildren():
                        parent.insert(parent.index(incl), ch)
                    parent.remove(incl)

            # document.fn = 
            log.debug("article document.fn = %r" % document.fn)
            document.write()
            documents.append(document)
        return documents

    def styles(self):
        return ICML(root=self.read('Resources/Styles.xml')).styles()

    def stylesheet(self, fn=None):
        """return a stylesheet from the .idml file's style definitions"""
        if fn is None:
            fn = os.path.join(self.output_path, os.path.basename(self.output_path)+'.css')
        return ICML(root=self.read('Resources/Styles.xml')).stylesheet(fn=fn)

