import os

from bxml import XML

from bkgen import NS

from .source import Source


class AID(XML, Source):
    NS = NS
    ROOT_TAG = "{%(pub)s}document" % NS

    def document(self, fn=None, **params):
        from .converters.aid_document import AidDocument

        converter = AidDocument()
        fn = fn or os.path.splitext(self.clean_filename(self.fn))[0] + ".xml"
        doc = converter.convert(self, fn=fn, **params)
        return doc

    def documents(self, fn=None, **params):
        return [self.document(fn=fn, **params)]
