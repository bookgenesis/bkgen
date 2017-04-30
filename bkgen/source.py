
from bl.file import File

class Source(File):
    """Base class/mixin for supported source formats. All sources must have the following properties/methods:
    fn          -- the filesystem path (filename) of the source, or None
    write()     -- to write the source to the filesystem
    documents   -- a list of pub:documents in the source or []
    images      -- a list of Image(File) objects or []
    metadata    -- a Metadata(XML) object or None
    stylesheet  -- a CSS(File) object or None
    """

    @property
    def documents(self):
        raise NotImplementedError

    @property
    def images(self):
        raise NotImplementedError

    @property
    def metadata(self):
        raise NotImplementedError

    @property
    def stylesheet(self):
        raise NotImplementedError
