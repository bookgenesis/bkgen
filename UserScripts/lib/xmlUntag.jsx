/*
untag the XML in the current document
*/

#include "./namespaces.js";

function xmlUntagBody(doc) {
	var doc = doc || app.activeDocument;
	var root = doc.xmlElements[0];
	var xmlElements = root.evaluateXPathExpression("//html:body", NAMESPACES);
	for (var i = 0; i < xmlElements.length; i++) {
		var elem = xmlElements[i];
		elem.untag();
	}
}

function xmlRemoveRoot(doc) {
	var doc = doc || app.activeDocument;
	var root = doc.xmlElements[0];
	root.remove();	
}
