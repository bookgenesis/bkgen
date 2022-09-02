from bl.file import File


class Source(File):
    """
    Base class/mixin for supported source formats.
    """

    def documents(self, path=None, **params):
        """
        Return a list of XML documents, with the root element tag pub:document, from the
        Source.
        """
        doc = self.document(path=path, **params)
        if doc is not None:
            return [doc]
        else:
            return []

    def document(self, path=None, **params):
        return

    def images(self):
        """returns a list of bf.image.Image objects provided by the Source."""
        return []

    def metadata(self):
        """
        Return a :doc:`bkgen.metadata.Metadata </api/metadata>` object provided by the
        Source, or None.
        """
        return None

    def stylesheet(self):
        """
        Return a :doc:`bkgen.css.CSS </api/css>` stylesheet object provided by the
        Source, or None.
        """
        return None
