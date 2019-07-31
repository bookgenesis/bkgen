from bl.file import File


class Source(File):
    """Base class/mixin for supported source formats. All sources must have the following properties and methods.
    
    **fn**    
        the filesystem path (filename) of the source, or None
    
    **write()**
        to write the source to the filesystem
    """

    def documents(self, path=None, **params):
        """returns a list of XML documents, with the root element tag pub:document, from the Source.
        """
        doc = self.document(path=path, **params)
        if doc is not None:
            return [doc]
        else:
            return []

    def document(self, path=None, **params):
        return

    def images(self):
        """returns a list of bf.image.Image objects provided by the Source.
        """
        return []

    def metadata(self):
        """returns a :doc:`bkgen.metadata.Metadata </api/metadata>` object provided by the Source, or None.
        """
        return None

    def stylesheet(self):
        """returns a :doc:`bkgen.css.CSS </api/css>` stylesheet object provided by the Source, or None.
        """
        return None
