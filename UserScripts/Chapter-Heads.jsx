
// Adjust layout for each chapter heading.
// This function needs to be generalized for use with any book.
function fixChapterHeads(document) {
	document = document || app.activeDocument;
	var stories = document.stories;
	var masters = {};
	for (var i=0; i < document.masterSpreads.length; i++) {
		$.writeln(document.masterSpreads[i].name);
		masters[document.masterSpreads[i].name] = document.masterSpreads[i];
	}
	var editedFrame;
	for(var i=0; i < stories.length; i++) {
		var story = stories[i];
		for (var j=0; j < story.paragraphs.length; j++) {
			var p = story.paragraphs[j];
			var pstyle = p.appliedParagraphStyle.name;
			if (p.parentTextFrames[0]!=editedFrame) {
				if (pstyle=='Chapter Title' || pstyle=='Endmatter Title') {
					$.writeln(pstyle + ': ' + p.contents);
					editedFrame = p.parentTextFrames[0];
					// editedFrame.textFramePreferences.insetSpacing = [4.25, 0, 0, 0];
					editedFrame.parentPage.appliedMaster = masters["A-Master"];
				// } else if (pstyle.match(/Copyright/)) {
				// 	editedFrame = p.parentTextFrames[0]
				// 	editedFrame.textFramePreferences.insetSpacing = [0, 0, 0.667, 0];
				// } else if (pstyle.match(/Body/)) {
				// 	editedFrame = p.parentTextFrames[0]
				// 	editedFrame.textFramePreferences.insetSpacing = [0, 0, 0, 0];
				// 	editedFrame.parentPage.appliedMaster = masters["I-Interior"];
				}
			} 
		}
	}
}

fixChapterHeads();