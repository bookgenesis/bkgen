
#include "./logger.js";

// check out all linked (incopy) stories
function icmlCheckOutStories(doc) {
	doc = doc || app.activeDocument;
	for (i=0; i < doc.stories.length; i++) {
		if (doc.stories[i].itemLink) {
			doc.stories[i].checkOut();
		}
	}
}

// check in all linked (incopy) stories
function icmlCheckInStories(doc) {
	doc = doc || app.activeDocument;
	for (i=0; i < doc.stories.length; i++) {
		if (doc.stories[i].itemLink) {
			doc.stories[i].checkIn();
		}
	}
}

function icmlUnlinkStories(doc) {
	doc = doc || app.activeDocument;
	for (i=doc.links.length - 1; i >= 0; i--) {
		var link = doc.links[i];
		if (link.name.match(/\.icml$/i)) {
			link.unlink();
		}
	}	
}

// export the content stories in the document to incopy
function icmlExportStories(doc) {
	doc = doc || app.activeDocument;
	var storyFolder = Folder(doc.filePath.toString() + '/Links');
	if (!storyFolder.exists) storyFolder.create();
	LOG(doc.fullName + ": " + doc.stories.length + " stories");

	// all document stories to .icml -- but only those that are not already!
	for (var i = 0; i < doc.stories.length; i++) {
		try{
			var story = doc.stories[i];
			var storyName = doc.name.replace(/\.[^\.]+$/, '') + '_' + i + '.icml';
			if (!story.itemLink
				&& story.textContainers.length > 0
				&& story.textContainers[0].toString().match(/TextFrame/i)
				&& story.textContainers[0].parentPage.isValid
				&& !story.textContainers[0].parentPage.parent.toString().match(/MasterSpread/i)
				&& (story.pageItems.length > 0 || !story.contents.match(/^$/))
			) {
				var storyFile = File(storyFolder.fullName + '/' + storyName);
				if (storyFile.exists) {
					storyFile.remove();
				}
				story.name = storyFile.name.replace(/\.[^\.]+$/, '');
				if (!storyFile.parent.exists) {
					storyFile.parent.create();
				}
				story.exportFile(ExportFormat.INCOPY_MARKUP, storyFile);
				LOG('exported ' + storyFile.fullName, LOG_LEVEL.INFO);
			}	
		} catch (err) {
			LOG(i + ': ' + err.message);
		}
	}
}
