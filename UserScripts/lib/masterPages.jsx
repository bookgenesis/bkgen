
#include "./json/json2.js";
#include "./array.js";
#include "./object.js";

// these paragraph styles only occur on these masters.
var STYLE_MASTERS = {
	'Title': 'A-Master',
	'Copyright': 'A-Master',
	'Endmatter Title': 'A-Master',
	'Toc Title': 'A-Master',
	'Chapter Title': 'A-Master',
}
var STYLES = STYLE_MASTERS.keys();

function pageStyles(page) {
	var pstyles = [];
	for (var i=0; i < page.textFrames.length; i++) {
		for (var j=0; j < page.textFrames[i].paragraphs.length; j++) {
			var para = page.textFrames[i].paragraphs[j];
			pstyles.push(para.appliedParagraphStyle.name);
		}
	}
	return pstyles;	
}

function masterPages(doc) {
	var doc = doc || app.activeDocument;
	for (var i=0; i < doc.pages.length; i++) {
		var page = doc.pages[i];
		var master = page.appliedMaster;
		var pstyles = pageStyles(page);
		for (j=0; j < STYLES.length; j++) {
			var style = STYLES[j];
			if (pstyles.contains(style)) {
				newMaster = doc.masterSpreads.itemByName(STYLE_MASTERS[style]);
				if (newMaster.name != master.name) {
					page.appliedMaster = newMaster;
				}
				break;
			}
		}
	}
}
