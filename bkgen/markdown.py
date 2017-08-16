
import os, tempfile
from lxml import etree
from bl.text import Text
from bxml.builder import Builder
from bkgen import NS
from bkgen.document import Document
from bkgen.source import Source
B = Builder(default=NS.html, **{'html':NS.html,'pub':NS.pub})

class Markdown(Text, Source):

    def document(self, fn=None, **params):
        """convert a markdown file into a pub:document via HTML"""
        from markdown import markdown
        content = markdown(self.text, output_format='xhtml5', lazy_ol=False)
        section = etree.fromstring("""<section id="s1" xmlns="%s">\n%s\n</section>""" % (NS.html, content))
        root = B.pub.document('\n\t', B.html.body('\n', section, '\n\t'), '\n')
        doc = Document(root=root, fn=fn or os.path.splitext(self.fn)[0]+'.xml')
        return doc

    def documents(self, **params):
        return [self.document(**params)]

