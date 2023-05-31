
#include "./conditions.jsx";
#include "./icml.jsx";

function insertPageNumberNotes(doc) {
	if (app.documents.length==0) {
		alert("Open a Document.\nA document needs to be open for this script to run.");
		return;
	}
	doc = doc || app.activeDocument;

	var quotePref = doc.textPreferences.typographersQuotes;
	doc.textPreferences.typographersQuotes = false;
	
	showAllConditions(doc);
	deletePageNumberNotes(doc);
	hideConditions(/digital/i, doc);
	
	for (var i=0; i < doc.pages.length; i++) {
		for (var j=0; j < doc.pages[i].textFrames.length; j++) {
			var frame = doc.pages[i].textFrames[j];
			if (frame && frame.parentPage && frame.parentPage.isValid && frame.insertionPoints[0].isValid) {
				var pageName = frame.parentPage.name;
				var note = frame.insertionPoints[0].notes.add();
				note.insertionPoints[0].contents = "<page n=\"" + pageName + "\"/>";
			}
		}
	}

	doc.textPreferences.typographersQuotes = quotePref;
}

// deletes all Notes containing <pub:page n="..."/> as the text
function deletePageNumberNotes(doc) {
	doc = doc || app.activeDocument;
	for (var i=0; i < doc.stories.length; i++) {
		for (var j=doc.stories[i].notes.length; j > -1; j--) {
			var note = doc.stories[i].notes[j];
			if (!note.isValid) continue;
			for (var k=0; k < note.texts.length; k++) {
				if (note.texts[k].contents.match(/^<(pub.)?page /)) {
					note.remove();
					break;
				}
			}
		}
	}
}
