
import os, tempfile
from lxml import etree
from bl.text import Text
from bxml.builder import Builder
from bkgen import NS
from bkgen.html import HTML
from bkgen.source import Source
B = Builder(default=NS.html, **{'html':NS.html,'pub':NS.pub})

class Markdown(Text, Source):

    def document(self, **params):
        """convert a markdown file into a pub:document via HTML"""
        doc = self.html().document()
        return doc

    def documents(self, **params):
        return [self.document(**params)]

    def html(self, reload=False):        
        if reload==True or self.__HTML is None:
            from markdown import markdown
            content = markdown(self.text, output_format='xhtml5', lazy_ol=False)
            body = etree.fromstring("""<body xmlns="%s">\n%s\n</body>""" % (NS.html, content))
            root = B.html.html('\n\t', body, '\n')
            self.__HTML = HTML(root=root, fn=os.path.splitext(self.fn)[0]+'.html')
        return self.__HTML

    def stylesheet(self):
        return self.html().stylesheet()
