
#include "./namespaces.js";

function fixSpecialCharacters(doc) {
	doc = doc || app.activeDocument;
	$.hiresTimer
	$.writeln("[" + Date().toString() + "] fixSpecialCharacters()");
	insertElementText(".//pub:x000A", '\r', doc);				// paragraph return
	insertElementText(".//pub:x202F", '\u202F', doc);			// narrow non-breaking space
	// insertElementText(".//pub:x2011", SpecialCharacters.NONBREAKING_HYPHEN, doc);
	insertElementText(".//pub:x2002", SpecialCharacters.EN_SPACE, doc);
	insertElementText(".//pub:x2003", SpecialCharacters.EM_SPACE, doc);
	// insertElementText(".//pub:x200A", SpecialCharacters.HAIR_SPACE, doc);
	// insertElementText(".//pub:x2009", SpecialCharacters.THIN_SPACE, doc);
	// insertElementText(".//pub:x2007", SpecialCharacters.FIGURE_SPACE, doc);
	// insertElementText(".//pub:x00AD", SpecialCharacters.DISCRETIONARY_HYPHEN, doc);
	insertElementText(".//pub:x00A0", SpecialCharacters.NONBREAKING_SPACE, doc);
	// insertElementText(".//pub:x2008", SpecialCharacters.PUNCTUATION_SPACE, doc);
	insertElementText(".//pub:tab[not(@indent)]", '\t', doc);	// (regular) tab
	insertElementText(".//pub:tab[@indent='right']", SpecialCharacters.RIGHT_INDENT_TAB, doc);
	// insertElementText(".//pub:tab[@indent='here']", SpecialCharacters.INDENT_HERE_TAB, doc);
	insertElementText(".//pub:linebreak | .//html:br", SpecialCharacters.FORCED_LINE_BREAK, doc);
	insertElementText(".//pub:colbreak", SpecialCharacters.COLUMN_BREAK, doc);
	insertElementText(".//pub:framebreak", SpecialCharacters.FRAME_BREAK, doc);
	// insertElementText(".//pub:pagebreak[not(@class)]", SpecialCharacters.PAGE_BREAK, doc);
	// insertElementText(".//pub:pagebreak[@class='even']", SpecialCharacters.EVEN_PAGE_BREAK, doc);
	// insertElementText(".//pub:pagebreak[@class='odd']", SpecialCharacters.ODD_PAGE_BREAK, doc);
	// insertElementText(".//pub:end-nested-style", SpecialCharacters.END_NESTED_STYLE, doc);
	return $.hiresTimer;
}

function insertElementText(xpath, text, doc) {
	// $.writeln(xpath);
	var position = XMLElementPosition.ELEMENT_END;
	doc = doc || app.activeDocument;
	for (i=0; i < doc.xmlElements.length; i++) {
		var elems = doc.xmlElements[i].evaluateXPathExpression(xpath, NS);
		for (j=0; j < elems.length; j++) {
			elems[j].insertTextAsContent(text, position);
		}
	}	
}

