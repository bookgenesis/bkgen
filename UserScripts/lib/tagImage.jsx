#include "./lib/markup.jsx";
#include "./lib/fs.jsx";

function tagImage(document) {
	document = document || app.activeDocument;
	if (!selectionEditable(document)) {
		alert("Please select an editable text location in the document.");
		return;
	}

	var file = File.openDialog("Select an image",null,false);
	if (file) { 
		var src = fs.relPath(file.fsName, app.activeDocument.filePath);
		var alt = getSelectionContents(document).replace(/s+/g, ' ');
		var img = XML('<img src="' + src + '" alt="' + alt + '"/>');
		tagSelection({
			start: img.toXMLString(),
		});
	}
}
