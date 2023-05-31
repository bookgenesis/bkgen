
function removeEmptyTextFrames(doc) {
	doc = doc || app.activeDocument;
	for (var i = doc.textFrames.length - 1; i >= 0; i--) {
		var textFrame = doc.textFrames[i];
		if (textFrame.pageItems.length==0 && textFrame.contents.length==0) {
			textFrame.remove();
		}
	}
}