
#include "./array.js";
#include "./logger.js";
#include "./utilities.js";

// apply the given functions to all documents in the documentFiles array
function allDocuments(docFiles, functions, params, options) {
	params = params || {};
	options = options || {'close': true, 'save': true};
	// allow the input to be a function or an array of functions
	if (typeof(functions)=='function') {
		var functions = [functions];
	}
	var time = 0;
	var openDocNames = app.documents.everyItem().fullName;
	var docFile = docFiles.shift();
	while (docFile) {
		LOG(docFile);

		var doc = app.open(docFile, true);	// show the window
		// apply the given function(s) in order
		for (i=0; i < functions.length; i++) {
			var fn = functions[i];
			if (fn) {
				fn(doc, params);
			}
		}
		if (options.close) {
			doc.close(SaveOptions.YES);
		} else if (options.save) {
			doc.save();
		}
		docFile = docFiles.shift();
	}
	for (var i = 0; i < openDocNames.length; i++) {
		app.open(openDocNames[i], true);
	}
}