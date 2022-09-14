import logging
from copy import deepcopy
from glob import glob
from pathlib import Path

import yaml
from bl.string import String
from bxml.builder import Builder
from lxml import etree

from bkgen.document import Document

log = logging.getLogger(__name__)
B = Builder(**Document.NS)


def import_resources(resource_map_filename, postprocess=None):
    path = Path(resource_map_filename).parent
    resource_map = yaml.safe_load(open(resource_map_filename).read())
    content_documents = {}
    for source_def in resource_map.get('sources') or []:
        log.debug(source_def)
        source_filenames = sorted(
            glob(str(path / source_def['source-path'] / source_def['file-glob']))
        )
        for source_filename in source_filenames:
            source_path = Path(source_filename)
            source_document = Document(fn=str(source_path))
            if source_path.name not in content_documents:
                content_documents[source_path.name] = Document()
                content_documents[source_path.name].fn = str(
                    path / 'content' / source_path.name
                )
            content_document = content_documents[source_path.name]
            log.info("content_document.fn = %s" % content_document.fn)
            content_document_body = content_document.find(
                content_document.root, "html:body"
            )
            assert content_document_body is not None
            for item in resource_items(source_document, source_def):
                content_document_body.append(item)
                log.debug(item.attrib)
            content_document.write()

    for document_def in resource_map.get('documents') or []:
        if document_def['name'] not in content_documents:
            content_document = Document()
            content_document.fn = str(path / 'content' / document_def['name'])
        content_document = content_documents[document_def['name']]
        log.info("content_document.fn = %s" % content_document.fn)
        content_document_body = content_document.find(
            content_document.root, "html:body"
        )
        assert content_document_body is not None
        for item in document_definition_items(document_def):
            content_document_body.append(item)
            log.debug(item.attrib)
        content_document.write()

    content_filenames = [
        str(path / 'content' / name) for name in content_documents.keys()
    ]

    if postprocess is not None:
        if not isinstance(postprocess, list):
            postprocess = [postprocess]
        for content_filename in content_filenames:
            for fn in postprocess:
                fn(content_filename)

    return content_filenames


def resource_items(source_document, source_def):
    for resource_items_def in source_def['definitions']:
        for item in resource_definition_items(source_document, resource_items_def):
            yield item


def resource_definition_items(source_document, resource_items_def):
    log.debug("resource_items_def['xpath'] = %r" % resource_items_def['xpath'])
    for element in source_document.xpath(
        source_document.root, resource_items_def['xpath']
    ):
        if element.tag == "{%(html)s}section" % Document.NS:
            section_item = deepcopy(element)
        else:
            section_item = B.html.section(deepcopy(element))

        # section class
        if resource_items_def.get('section-class'):
            section_item.set('class', resource_items_def['section-class'])

        # title
        if resource_items_def.get('title'):
            section_item.set('title', resource_items_def.get('title'))
        elif resource_items_def.get('title-xpath'):
            section_item.set(
                'title',
                str(
                    ''.join(Document.xpath(element, resource_items_def['title-xpath']))
                ),
            )

        # data-ref
        if resource_items_def.get('ref-xpath'):
            section_item.set(
                'data-ref',
                str(''.join(Document.xpath(element, resource_items_def['ref-xpath']))),
            )

        # collect next matches
        if resource_items_def.get('collect-next-matches'):
            collect_next_matches = resource_items_def['collect-next-matches']
            log.debug('collect_next_matches = %r' % collect_next_matches)
            next_elem = element.getnext()
            while (
                next_elem is not None
                and Document.find(next_elem, f"self::{collect_next_matches}")
                is not None
            ):
                section_item.append(deepcopy(next_elem))
                next_elem = next_elem.getnext()

        # id
        if section_item.get('id') is not None:
            section_item.attrib.pop('id')
        section_item.set('id', element_content_id(section_item))

        section_item.text = '\n'
        section_item.tail = '\n\n'
        yield section_item


def document_definition_items(document_def):
    template = document_def['template']
    for item_def in document_def['items']:
        section_item = etree.fromstring(template.format(**item_def))
        section_item.tail = '\n\n'
        if section_item.get('id') is not None:
            section_item.attrib.pop('id')
        section_item.set('id', element_content_id(section_item))
        yield section_item


def element_content_id(element):
    """create an id for the element based on its content"""
    return '_' + String(Document.canonicalized_string(element)).digest(
        b64=True, alg='md5'
    )
