
import logging
log = logging.getLogger(__name__)

import os
from lxml import etree
from bl.dict import Dict
from bl.file import File
from bl.id import random_id
from bl.zip import ZIP
from bl.string import String
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
    def design_map(self, path=None):
        path = path or self.output_path
        return ICML(root=self.read('designmap.xml'))

    def items_dict(self):
        """returns a dict of items (anything with a Self) in the IDML file. Needed to resolve Article components."""
        d = Dict()
        for rp in [rp for rp in self.zipfile.namelist() if os.path.splitext(rp)[-1].lower()=='.xml']:
            x = XML(root=self.read(rp))
            for item in x.root.xpath("//*[@Self] | //idPkg:*[@Self]", namespaces=self.NS):
                if item.get('Self') in d and d[item.get('Self')].attrib != item.attrib:
                    log.error("%s already in items_dict. %r vs. %r" % (item.get('Self'), d[item.get('Self')].attrib, item.attrib))
                else:
                    d[item.get('Self')] = item
        return d

    def documents(self, path=None, articles=True, **params):
        """return a collection of pub:documents from the stories in the .idml file.
        If the .idml file has Articles, use those as guidance; otherwise, use the stories directly.
        """
        path = path or self.output_path
        designmap = self.design_map(path=path)
        documents = []
        # output all stories
        for story in designmap.root.xpath("idPkg:Story", namespaces=self.NS):
            outfn = os.path.join(path, self.clean_filename(self.basename), story.get('src'))
            icml = ICML(fn=outfn, root=self.read(story.get('src')))
            document = icml.document(fn=outfn)
            document.write()
            documents.append(document)
        # if there are articles, they are also output (composed of stories)
        if articles==True and len(designmap.root.xpath("//Article")) > 0:
            documents += self.articles_documents(path=path, designmap=designmap)
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

    def articles_documents(self, path=None, designmap=None):
        """return a collection of pub:documents built from the InDesign Articles in the .idml file.
        (Articles are composed of stories, so use pub:include to link to the stories)
        """
        from bxml.builder import Builder
        from bkgen.document import Document
        B = Builder(default=NS.html, **{'html':NS.html, 'pub':NS.pub})
        path = path or self.output_path
        designmap = designmap or self.design_map()
        itemsdict = self.items_dict()
        documents = []
        for article in designmap.root.xpath("//Article"):
            body = B._.body('\n')
            document = Document(
                root=B.pub.document('\n', body, '\n'),
                fn=os.path.join(path, self.clean_filename(self.basename), self.clean_filename((article.get('Name') or article.get('Self'))+'.xml')))
            log.debug(document.fn)
            for member in article.xpath("ArticleMember"):
                item = itemsdict[member.get('ItemRef')]
                log.info("ItemRef=%r => %r ParentStory=%r" % (member.get('ItemRef'), item.tag, item.get('ParentStory')))
                for elem in item.xpath("descendant-or-self::*[@ParentStory]"):
                    story_id = elem.get('ParentStory')
                    pkg_story = designmap.find(designmap.root, 
                        "//idPkg:Story[contains(@src, '%s')]" % story_id, namespaces=ICML.NS)

                    # add a <pub:include...> element for the story
                    incl = etree.Element("{%(pub)s}include" % NS, src=pkg_story.get('src')); incl.tail='\n'
                    body.append(incl)

                    # make sure the story exists in the content
                    story_outfn = os.path.join(path, self.clean_filename(self.basename), pkg_story.get('src'))
                    if not os.path.exists(story_outfn):
                        story_icml = ICML(fn=outfn, root=self.read(pkg_story.get('src')))
                        story_doc = icml.document(fn=outfn)
                        story_doc.write()
                        documents.append(story_doc)
            document.write()
            documents.append(document)
            log.debug(document.fn)
        return documents

    def stylesheet(self, fn=None):
        """return a stylesheet from the .idml file's style definitions"""
        if fn is None:
            fn = os.path.join(self.output_path, os.path.basename(self.output_path)+'.css')
        return ICML(root=self.read('Resources/Styles.xml')).stylesheet(
            fn=fn)

