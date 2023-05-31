
function listBookmarkNames(document) {
	document = document || app.activeDocument;
	for (i=0; i<document.bookmarks.length; i++) {
		var b = document.bookmarks[i];
		$.writeln(b.name + ' => ' + b.destination.name);
	}

}

listBookmarkNames();