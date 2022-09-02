class Converter:
    """abstract base class for converters. Required interface:
    >>> source_obj = "This is a source"           # would usually be an instance of a content class
    >>> converter = Converter()                   # initialization params available, not required
    >>> dest_obj = converter.convert(source_obj)  # returns dest_obj from the conversion
    """

    def convert(self, source_obj, **params):
        raise NotImplementedError(
            "This method needs to be implemented in %s" % self.__class__.__name__
        )
