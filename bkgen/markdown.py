
import os, tempfile
from lxml import etree
import markdown.extensions.wikilinks
from bl.text import Text
from bxml.builder import Builder
from bkgen import NS
from bkgen.html import HTML
from bkgen.source import Source
B = Builder(default=NS.html, **{'html':NS.html,'pub':NS.pub})

class Markdown(Text, Source):

    EXTENSIONS = [
        'markdown.extensions.extra',
        'markdown.extensions.admonition',
        # 'markdown.extensions.codehilite',
        'markdown.extensions.headerid',
        # 'markdown.extensions.meta',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
        # 'markdown.extensions.smarty',
        'markdown.extensions.toc',
        markdown.extensions.wikilinks.WikiLinkExtension(base_url='', end_url='.html'),
    ]

    def document(self, **params):
        """convert a markdown file into a pub:document via HTML"""
        doc = self.html().document()
        return doc

    def documents(self, **params):
        return [self.document(**params)]

    def html(self, reload=False, output_format='xhtml5', lazy_ol=False, extensions=None):        
        if reload==True or self.__HTML is None:
            from markdown import markdown
            content = markdown(self.text, output_format=output_format, lazy_ol=lazy_ol, extensions=extensions or self.EXTENSIONS)
            body = etree.fromstring("""<body xmlns="%s">\n%s\n</body>""" % (NS.html, content))
            root = B.html.html('\n\t', body, '\n')
            for e in root.xpath("//*[contains(@href, '.md')]"):
                l = e.get('href').split('#')
                l[0] = os.path.splitext(l[0])[0] + '.html'
                e.set('href', '#'.join(l))
            self.__HTML = HTML(root=root, fn=os.path.splitext(self.fn)[0]+'.html')
        return self.__HTML

    def stylesheet(self):
        return self.html().stylesheet()
