
function exportIDML(doc) {
	$.hiresTimer;
	doc = doc || app.activeDocument;
	var expFile = File(doc.fullName.fsName.replace(/\.[^\.]+$/, ".idml"));
	$.writeln(expFile);
	doc.exportFile(ExportFormat.INDESIGN_MARKUP, expFile, false, app.pdfExportPresets.firstItem(), "", true);
	return $.hiresTimer;
}

var total = 0;
for (i=0; i < app.documents.length; i++) {
	var doc = app.documents[i];
	var time = 	exportIDML(doc);
	$.writeln("[" + Date().toString() + "] " + doc.name);
	total += time;
}
$.writeln("[" + Date().toString() + "] total = " + total/1e6 + ' s');