/*
Package the activeBook for Print and Digital production.
*/

#include "../lib/bookAll.jsx";
#include "../lib/pageNumberNotes.jsx";
#include "../lib/conditions.jsx";
#include "../lib/icml.jsx";
#include "../lib/json/json2.js";
#include "../lib/exportDocument.jsx";
#include "../lib/allDocuments.jsx";
#include "../lib/bookManifest.jsx";

var saveFolder = Folder(app.activeBook.fullName.toString().replace(/\.[^\.]+$/, '-package'));
if (!saveFolder.exists) {
	saveFolder.create();
}
LOG("Export " + app.activeBook.fullName + ' to ' + saveFolder);

// remove previously-exported files
var previousFiles = saveFolder.getFiles();
for (var i=0; i < previousFiles.length; i++) {
	if (previousFiles[i].exists) {
		previousFiles[i].remove();
	}
}
var previousLinks = Folder(saveFolder.fullName + '/Links').getFiles();
for (var i=0; i < previousLinks.length; i++) {
	if (previousLinks[i].exists) {
		previousLinks[i].remove();
	}
}

app.activeBook.preflight(
	File(saveFolder.fullName + '/' + app.activeBook.name.replace(/\.indb/i, '-preflight.txt')),
	false	// autoOpen
);

app.activeBook.packageForPrint(
	saveFolder, 
	true, 			// copyingFonts
	true, 			// copyingLinkedGraphics
	true, 			// copyingProfiles
	true, 			// updatingGraphics
	false, 			// includingHiddenLayers
	true, 			// ignorePreflightErrors
	false, 			// creatingReport
	false, 			// includeIdml -- will be included in exportDocument, below
	false,			// includePdf
	"", 			// versionComments
	false			// forceSave
);

// do the export on the packaged documents
inddFiles = saveFolder.getFiles("*.indd");
allDocuments(inddFiles, exportDocument, {"reopen": false}, {"close": false});

// create a .json manifest of the new book
var newBook = app.open(File(saveFolder.fullName + '/' + app.activeBook.name));
var manifestFile = bookManifest(newBook);
newBook.close();

// // don't keep .indd or .indb files in the package -- we just want the .idml
// var indFiles = saveFolder.getFiles("*.ind?");
// for (var i=indFiles.length - 1; i >= 0; i--) {
// 	indFiles[i].remove();
// }

LOG("finished packaging book.");
