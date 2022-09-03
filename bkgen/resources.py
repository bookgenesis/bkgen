"""
Process a set of content into the project resources/ folder using a resources.yaml file.

* resources = a dict of resources, each naming a resources/ subfolder, and defining the
  sources and transformations of that content. Output files have the same names as input
    + sources = a list of project-relative paths for XML content
    + transforms = a list of transformation scripts to run, in order, on the sources

    TODO: Process non-XML resources (cf. tecarta-python storyboard)

All paths in the resources.yaml are relative to the parent directory of that document.

(This module is based on and inspired by earlier work for Tecarta. That work proved not
very generalizable and included a lot of bespoke scripting. This is more generic.)
"""

import multiprocessing as mp
import os
import shutil
import traceback
from glob import glob
from importlib import import_module
from pathlib import Path
from typing import List

import click
import yaml
from bl.rglob import rglob
from bxml.builder import Builder
from bxml.xslt import XSLT
from pydantic import BaseModel, Field, validator

from bkgen.document import Document

PATH = Path(os.path.abspath(__file__)).parent


class Resource(BaseModel):
    folder: str
    sources: List[Path] = Field(default_factory=list)
    transforms: List[Path] = Field(default_factory=list)
    params: dict = Field(default_factory=dict)

    @validator('sources')
    def unpack_sources_globs(cls, value):
        """
        Any source that is a Path might be a glob. Unpack these first.
        """

        def gen_sources(value):
            for val in value:
                for path in glob(str(val)):
                    yield Path(path)

        return list(gen_sources(value))

    @validator('sources')
    def check_unique_sources(cls, value):
        """
        Each source must have a unique base filename within this Resource.
        """
        basenames = [source.name for source in value]
        assert len(basenames) == len(
            set(basenames)
        ), f"Non-unique source filenames: {value}"
        return value

    def process(self, pool=None):
        pool = pool or mp.Pool()
        for source in self.sources:
            yield pool.apply_async(self.process_source, (source,))

    def process_source(self, source):
        # * Assume all sources are bkgen.Document XML and all transforms are lxml XSLT.
        #   1. Load the document
        #   2. Apply any transforms
        #   3. Write the output document
        # * TODO: generalize
        resource_path = Path(self.folder) / source.name
        params = {
            **dict(
                doc_name=resource_path.stem,
                source=str(source),
                resource_path=str(resource_path),
            ),
            **self.params,
        }
        if source.suffix.lower() == '.xml':
            doc = Document(fn=str(source))
        else:
            doc = Document()
            if source.suffix:
                if resource_path.exists():
                    os.remove(resource_path)
                shutil.copy(source, resource_path)
        try:
            for transform in self.transforms:
                # xsl module, to be processed by lxml XSLT
                if 'xsl' in transform.suffix:
                    xslt = XSLT(fn=str(transform))
                    doc.root = xslt(doc.root, **params).getroot()

                # python 'module:method', callable with doc.root and **params
                elif ':' in str(transform):
                    modname, trfname = str(transform).split(':')
                    mod = import_module(modname)
                    trf = mod.__dict__[trfname]
                    doc.root = trf(doc.root, **params)

            body = doc.find(doc.root, 'html:body')

            # write files that have content
            if body is not None and body.getchildren():
                doc.fn = os.path.splitext(resource_path)[0] + '.xml'
                doc.write()

            # remove left-over empty files
            else:
                fn = os.path.abspath(str(resource_path))
                if os.path.exists(fn):
                    print('REMOVE', resource_path)
                    os.remove(fn)

        except Exception as exc:
            print(self.folder, source, transform, exc)
            print(traceback.format_exc())

        return resource_path


class Resources(BaseModel):
    """
    The content of a resources.yaml document.

    * resources = a list of Resource definitions. Each one must have a unique `folder`
    """

    # **TODO**: semantic versioning string for comparison with this version?
    version: str = '0.0.1'
    resources: List[Resource] = Field(default_factory=list)

    @validator('resources')
    def check_unique_folders(cls, value):
        """
        Each Resource in this Resources list must have a unique folder name
        """
        folders = [resource.folder for resource in value]
        assert len(folders) == len(
            set(folders)
        ), f"Non-unique resource folders: {folders}"
        return value

    @classmethod
    def load(cls, filename):
        """
        Load the Resources from the given filename.
        """
        with open(filename) as f:
            return cls(**yaml.safe_load(f.read()))

    def process(self, folder=None):
        """
        Process the Resources as defined. Parameters:

        * folder - if given, limit to processing only this resource.folder value (useful
          during development). Default is to process all resources.

        Uses parallel processing:

        * Each Resources writes to a unique folder, so can be parallelized.
        * All sources in each Resource write to unique files, so can be parallelized.
        """
        pool = mp.Pool()
        for resource in self.resources:
            # limit to folder if given
            if folder is not None and str(resource.folder) != str(folder):
                continue

            # ensure resource.folder exists, so different processes don't makedirs.
            os.makedirs(resource.folder, exist_ok=True)

            if not resource.sources:
                resource.sources = [Path(resource.folder)]

            for source in resource.sources:
                yield pool.apply_async(resource.process_source, (source,))


def update_spine(project):
    res = Resources.load(PATH / 'resources.yaml')
    PUB = Builder.single(Document.NS.pub)

    # collect all the included sections with filename#id
    includes = []
    for resource in res.resources:
        fns = rglob(str(PATH / resource.folder), '*.xml')
        for fn in fns:
            doc = Document(fn=fn)
            for incl in doc.xpath(doc.root, '//pub:include'):
                includes.append(incl.get('src').split('/')[-1])

    # create the spine with all the sections that are not included elsewhere
    spine = project.find(project.root, 'pub:spine')
    for resource in res.resources:
        fns = rglob(str(PATH / resource.folder), '*.xml')
        for fn in fns:
            basename = fn.split('/')[-1]
            doc = Document(fn=fn)
            for section in doc.xpath(doc.root, "html:body/html:section"):
                if f"{basename}#{section.get('id')}" not in includes:
                    relpath = os.path.relpath(doc.fn, str(PATH))
                    href = f"{relpath}#{section.get('id')}"
                    if project.find(spine, f"pub:spineitem[@href='{href}']") is None:
                        spineitem = PUB.spineitem({'href': href})
                        if section.get('title'):
                            spineitem.set('title', section.get('title'))
                        spineitem.tail = '\n\t'
                        spine.append(spineitem)
                        print('APPEND spineitem:', spineitem.attrib)


# == COMMAND-LINE INTERFACE ==


@click.group()
def main():
    pass


@main.command('process')
@click.argument('filename', type=click.Path(exists=True))
@click.option(
    '-f', '--folder', help='Limit to resources for the given folder, if given.'
)
def process_resources(filename, folder=None):
    """
    Process the resources defined in FILENAME
    """
    resources = Resources.load(filename)
    for result in resources.process(folder=folder):
        print(result.get())


if __name__ == '__main__':
    main()
