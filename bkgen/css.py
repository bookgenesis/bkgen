import logging

import bf.css
from bl.dict import Dict
from bxml import XML

from bkgen import NS

log = logging.getLogger(__name__)


class CSS(bf.css.CSS):
    def remove_unused_styles(self, xmlfns):
        """delete the styles that are not used in the given XML fns."""
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
                _ = self.styles.pop(sel)

    def add_undefined_styles(self, xmlfns):
        """add XML styles that are not defined in the stylesheet"""
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
