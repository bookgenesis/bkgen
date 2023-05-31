
// add a landmark nav label to the current bookmark, for EPUB

#include "./markup.jsx";
#include "./json/json2.js";

var document = app.activeDocument;
if (selectionExists(document)) {
	var selection = getSelection(document);
	alert(document.selection[0].hyperlinkTextDestinations.length);
}