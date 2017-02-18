
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

import os, sys
from bl.dict import Dict
from bl.file import File
from bl.string import String
from .styles import Styles
from pubxml import NS

class CSS(File):
    
    def __init__(self, fn=None, styles=None, encoding='UTF-8', **args):
        File.__init__(self, fn=fn, encoding=encoding, **args)
        if styles is not None:
            self.styles = styles
        elif fn is not None and os.path.exists(fn):
            self.styles = Styles.from_css(self.read().decode(encoding))
        else:
            self.styles = Styles()

    def write(self, fn=None, encoding='UTF-8', **args):
        data = Styles.render(self.styles).encode(encoding)
        super().write(fn=fn, data=data)

    def remove_unused_styles(self, xmlfns):
        """delete the styles that are not used in the given XML fns."""
        from bxml import XML
        selectors = []
        for fn in xmlfns:
            x = XML(fn=fn)
            for element in x.root.xpath("//html:*[@class]", namespaces=NS):
                for classname in element.get('class').split(' '):
                    selector = element.tag.split('}')[-1] + '.' + classname
                    selectors.append(selector)
        selectors = list(set(selectors))
        for sel in self.styles.keys():
            if sel not in selectors:
                log.debug("%s %r" % (sel, self.styles[sel]))
                _=self.styles.pop(sel)

    def add_undefined_styles(self, xmlfns):
        """add XML styles that are not defined in the stylesheet"""
        from bxml import XML
        selectors = []
        for fn in xmlfns:
            x = XML(fn=fn)
            for element in x.root.xpath("//html:*[@class]", namespaces=NS):
                for classname in element.get('class').split(' '):
                    selector = element.tag.split('}')[-1] + '.' + classname
                    selectors.append(selector)
        selectors = list(set(selectors))
        for sel in selectors:
            if sel not in self.styles.keys():
                log.debug("adding: %r" % sel)
                self.styles[sel] = Dict()

    @classmethod
    def merge_stylesheets(Class, fn, cssfns):
        """merge the given CSS files, in order, into a single stylesheet"""
        stylesheet = Class(fn=fn)
        for cssfn in cssfns:
            css = Class(fn=cssfn)
            for sel in sorted(css.styles.keys()):
                if sel not in stylesheet.styles:
                    stylesheet.styles[sel] = css.styles[sel]
                elif stylesheet.styles[sel] != css.styles[sel]:
                    log.warn("sel %r not equivalent:\n\t%s\n\t%s" % (sel, stylesheet.fn, css.fn))
                    log.warn("\n\t%r\n\t%r" % (stylesheet.styles[sel], css.styles[sel]))
        return stylesheet
