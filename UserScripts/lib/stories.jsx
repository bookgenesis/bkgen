#target "indesign";
#include "./fs.jsx";

var EXPORT_PARAMS = {
	format: ExportFormat.INCOPY_MARKUP,
	relPath: 'Export'
};


// export content stories as links (i.e., InCopy stories) if not already links.
// return => array of stories that were thus exported.
function exportStories(params, document) {
	params = params || {};
	for (var key in EXPORT_PARAMS) { params[key] = params[key] || EXPORT_PARAMS[key]; }
	document = document || app.activeDocument;
	var docFolder = Folder(document.filePath);
	exportFolder = Folder([document.filePath, params.relPath].join('/'));
	if (!exportFolder.exists) { exportFolder.create(); }
	var n = 0;									// counter for the stories that are made into links.
	var stories = document.stories.everyItem().getElements();
	for (var i=0; i < stories.length; i++) {
		var story = stories[i];
		if (storyIsContent(story)) {
			n = n + 1;
			if (story.itemLink) {story.itemLink.unlink();}
			story.name = storyContentTitle(story);
			var basename = storyIndexString(n) + '-' + story.name.replace(/\s+/g, "-") + '.icml';
			var storyFile = File(fs.absPath(exportFolder.fsName) + '/' + basename);
			if (storyFile.exists) {storyFile.remove();}
			story.exportFile(params.format, storyFile.fsName);
		}
	}
}


function contentStories(doc) {
	doc = doc || app.activeDocument;
	var stories = Array();
	for (var i=0; i < doc.stories.length; i++) {
		if (storyIsContent(doc.stories[i])) {
			stories.push(doc.stories[i]);
		}
	}
	return stories;
}


// return => true if the given story is a content story.
function storyIsContent(story) {
	var parentConstructor = story.textContainers[0].parent.constructor;
	for (i=0; i<story.parent.hyperlinkTextDestinations.length; i++) {
		var destText = story.parent.hyperlinkTextDestinations[i].destinationText;
		for (j=0; j < story.texts.length; j++) {
	        if (story.texts[i] === destText) {
	            return true;
	        }
	    }
	}
	if ((parentConstructor===MasterSpread || storyContentTitle(story).replace("/\s+/g", "")=="")
		&& story.notes.length==0) {
		return false;
	}
	return true;
}

// create a string from the story index, zero-padded with the number of digits needed.
// (use sprintf() once we have it tested and working in InDesign)
function storyIndexString(index, numchars, document) {
	document = document || app.activeDocument;
	numchars = numchars || document.stories.length.toString().length;
	var s = '' + index;
	while (s.length < numchars) { s = '0' + s; }
	return s;
}

// create a content title for the story, with at most numwords (default 6)
function storyContentTitle(story, numwords) {
	numwords = numwords || 6;
	var titleWords = Array();
	for (i=0; i < story.paragraphs.length; i++) {
		var para = story.paragraphs[i];
		for (j=0; j < para.texts.length; j++) {
			var words = para.texts[j].contents.split(/\s+/);
			for (k=0; k < words.length; k++) {
				var word = words[k].replace(/\W/g, "");
				if (word != "") {
					titleWords[titleWords.length] = word;
				}
				if (titleWords.length >= numwords) { break; }
			}
			if (titleWords.length >= numwords) { break; }
		}
		if (titleWords.length >= 0) { break; }	// don't go beyond one paragraph
	}
	return titleWords.join(" ");
}
