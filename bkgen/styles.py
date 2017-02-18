
import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

import sys
from bl.dict import Dict
from bl.string import String

class Styles(Dict):
    
    @classmethod    
    def render(c, styles, margin="", indent="\t"):
        """output css text from styles. 
        margin is what to put at the beginning of every line in the output.
        indent is how much to indent indented lines (such as inside braces)."""
        def render_dict(d):
            return ('{\n' 
                    + c.render(styles[k], 
                        margin=margin+indent,   # add indent to margin
                        indent=indent) 
                    + '}\n')
        s = ""
        # render the css text
        for k in styles.keys():
            s += margin + k + ' '
            if type(styles[k]) in [str, String]:
                s += styles[k] + ';'
            elif type(styles[k]) in [dict, Dict]:
                s += render_dict(styles[k])
            elif type(styles[k]) in [tuple, list]:
                for i in styles[k]:
                    if type(i) in [str, String]:
                        s += i + ' '
                    if type(i) == bytes:
                        s += str(i, 'utf-8') + ' '
                    elif type(i) in [dict, Dict]:
                        s += render_dict(i)
            else:
                s += ';'
            s += '\n'
        return s

    @classmethod
    def from_css(Class, csstext, encoding=None, href=None, media=None, title=None, validate=None):
        """parse CSS text into a Styles object, using cssutils"""
        import cssutils
        cssutils.log.setLevel(logging.FATAL)
        styles = Class()
        cssStyleSheet = cssutils.parseString(csstext, encoding=encoding, href=href, media=media, title=title, validate=validate)
        for rule in cssStyleSheet.cssRules:
            if rule.type==cssutils.css.CSSRule.FONT_FACE_RULE:
                pass
            
            elif rule.type==cssutils.css.CSSRule.IMPORT_RULE:
                pass
            
            elif rule.type==cssutils.css.CSSRule.NAMESPACE_RULE:
                pass
            
            elif rule.type==cssutils.css.CSSRule.MEDIA_RULE:
                pass
            
            elif rule.type==cssutils.css.CSSRule.PAGE_RULE:
                pass
            
            elif rule.type==cssutils.css.CSSRule.STYLE_RULE:
                for selector in rule.selectorList:
                    sel = selector.selectorText
                    if sel not in styles:
                        styles[sel] = Dict()
                    for property in rule.style.getProperties(all=True):
                        stylename = property.name + ':'
                        styles[sel][stylename] = property.value
                        if property.priority != '':
                            styles[sel][stylename] = ' !'+property.priority
            
            elif rule.type==cssutils.css.CSSRule.COMMENT:
                pass
            
            elif rule.type==cssutils.css.CSSRule.VARIABLES_RULE:
                pass
            
            else:
                log.warning("Unknown rule type: %r" % rule.cssText)

        return styles
