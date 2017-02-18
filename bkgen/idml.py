
import logging
log = logging.getLogger(__name__)

import os
from lxml import etree
from bl.dict import Dict
from bl.id import random_id
from bl.zip import ZIP
from bl.string import String
from bxml import XML
from .icml import ICML
import pubxml

class IDML(ZIP):
    POINTS_PER_EM = ICML.POINTS_PER_EM
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
                assert item.get('Self') not in d
                d[item.get('Self')] = item
        return d

    def documents(self, path=None, **params):
        """return a collection of pub:documents from the stories in the .idml file.
        If the .idml file has Articles, use those as guidance; otherwise, use the stories directly.
        """
        path = path if path is not None else self.output_path
        designmap = self.design_map(path=path)
        if len(designmap.root.xpath("//Article")) > 0:
            return self.articles_documents(path=path, designmap=designmap)
        else:
            documents = []
            for story in designmap.root.xpath("idPkg:Story", namespaces=self.NS):
                # use a temporary file for the story source, just in case it's huge
                tfn = os.path.join(os.path.dirname(self.fn), random_id())
                with open(tfn, 'wb') as tf:
                    tf.write(self.read(story.get('src')))
                root = etree.parse(tfn).getroot()
                os.remove(tfn)
                icml = ICML(root=root)
                document_fn = os.path.join(path, story.get('src'))
                log.debug(document_fn)
                document = icml.document(fn=document_fn)
                documents.append(document)
            # fix links between documents
            ids = {}
            for d in documents:
                for e in d.root.xpath("//*[@id]"):
                    ids[e.get('id')] = d.fn
            for doc in documents:
                for e in doc.root.xpath("//pub:include[@id]", namespaces=pubxml.NS):
                    if e.get('id') in ids:
                        id = e.attrib.pop('id')
                        targetfn = ids[id]
                        e.set('src', os.path.relpath(targetfn, os.path.dirname(doc.fn)) + '#' + id)
            return documents

    def articles_documents(self, path=None, designmap=None):
        """return a collection of pub:documents built from the InDesign Articles in the .idml file."""
        path = path if path is not None else self.output_path
        designmap = designmap or self.design_map()
        itemsdict = self.items_dict()
        documents = []
        for article in designmap.root.xpath("//Article"):
            icml = ICML(root=etree.Element('Document'))
            story_ids = []
            for member in article.xpath("ArticleMember"):
                item = itemsdict[member.get('ItemRef')]
                log.info("ItemRef=%r => %r ParentStory=%r" % (member.get('ItemRef'), item.tag, item.get('ParentStory')))
                if item.get('ParentStory') is not None:
                    story_id = item.get('ParentStory')
                    if story_id not in story_ids:
                        story = itemsdict[story_id]
                        log.info("    %r Self=%r" % (story.tag, story.get('Self')))
                        icml.root.append(story)
                        story_ids.append(story_id)
                else:
                    for elem in item.xpath(".//*[@ParentStory]", namespaces=self.NS):
                        story_id = elem.get('ParentStory')
                        log.info("  %r ParentStory=%r" % (elem, story_id))
                        if story_id not in story_ids:
                            story = itemsdict[story_id]
                            log.info("    %r Self=%r" % (story.tag, story.get('Self')))
                            icml.root.append(story)
                            story_ids.append(story_id)
            fb = "%s_%s.xml" % (self.basename, String(article.get('Name')).hyphenify())
            document_fn = os.path.join(path, fb)
            log.debug(document_fn)            
            document = icml.document(fn=document_fn)
            documents.append(document)
            log.debug(document.fn)
        return documents

    def stylesheet(self, fn=None, points_per_em=POINTS_PER_EM):
        """return a stylesheet from the .idml file's style definitions"""
        if fn is None:
            fn = os.path.join(self.output_path, os.path.basename(self.output_path)+'.css')
        return ICML(root=self.read('Resources/Styles.xml')).stylesheet(
            fn=fn, 
            points_per_em=points_per_em)

    def resources(self, path=None):
        """return a list of files representing the resources in the document"""
        return []

    def metadata(self, path=None):
        """return a list of files representing the resources in the document"""
        return []

