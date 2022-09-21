import os

import markdown.extensions.wikilinks
from bl.string import String
from bl.text import Text
from bl.url import URL
from bxml.builder import Builder
from lxml import etree

from bkgen import NS
from bkgen.html import HTML
from bkgen.source import Source

B = Builder(default=NS.html, **{"html": NS.html, "pub": NS.pub})


class Markdown(Text, Source):

    EXTENSIONS = [
        "markdown.extensions.extra",
        "markdown.extensions.admonition",
        "markdown.extensions.nl2br",
        "markdown.extensions.sane_lists",
        "markdown.extensions.toc",
        markdown.extensions.wikilinks.WikiLinkExtension(base_url="", end_url=".html"),
    ]

    def document(self, **params):
        """convert a markdown file into a pub:document via HTML"""
        doc = self.html().document()
        return doc

    def documents(self, **params):
        return [self.document(**params)]

    def html(
        self, reload=False, output_format="xhtml5", lazy_ol=False, extensions=None
    ):
        if reload is True or self.__HTML is None:
            from markdown import markdown

            content = markdown(
                self.text,
                output_format=output_format,
                lazy_ol=lazy_ol,
                extensions=extensions or self.EXTENSIONS,
            )
            body = etree.fromstring(
                """<body xmlns="%s">\n%s\n</body>""" % (NS.html, content)
            )
            root = B.html.html("\n\t", body, "\n")
            for elem in root.xpath("//*[contains(@href, '.md')]"):
                path_fragment = str(URL(elem.get("href"))).split("#")
                path_fragment[0] = os.path.splitext(path_fragment[0])[0] + ".html"
                elem.set("href", "#".join(path_fragment))
            for elem in root.xpath("//*[@id]"):
                elem.set("id", String(elem.get("id")).nameify())
            self.__HTML = HTML(root=root, fn=os.path.splitext(self.fn)[0] + ".html")
        return self.__HTML

    def stylesheet(self):
        return self.html().stylesheet()
