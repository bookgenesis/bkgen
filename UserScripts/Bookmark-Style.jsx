#include "./lib/string.js";

// bookmark the paragraphs in the document, by selected paragraph style

function bookmarkStyle(document) {
	document = document || app.activeDocument;
	var styleName = prompt("Paragraph style to bookmark:", "");
	if (styleName) {
		var stories = document.stories;
		for (var i=0; i < stories.length; i++) {
			for (var j=0; j < stories[i].paragraphs.length; j++) {
				var paragraph = stories[i].paragraphs[j];
				if (paragraph.appliedParagraphStyle.name==styleName) {
					var bookmarkText = trim(paragraph.contents);
					if (bookmarkText!="") {
						document.bookmarks.add(
							document.hyperlinkTextDestinations.add(
								paragraph.insertionPoints[0]),
							{'name': bookmarkText});
					}
				}
			}
		}
	}
}

bookmarkStyle();
