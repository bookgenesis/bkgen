
#include "./array.js";
#include "./logger.js";
#include "./utilities.js";

// apply the given function to every document in the active book
// params -- an object containing parameters for the function

function allDocs(functions, params, options) {
	params = params || {};
	options = options || {'close': true, 'save': true};
	// allow the input to be a function or an array of functions
	if (typeof(functions)=='function') {
		var functions = [functions];
	}
	var functionNames = [];
	for (i=0; i < functions.length; i++) {
		functionNames.push(functions[i].name)
	};
	var time = 0;
	var docNames = app.documents.everyItem().fullName;
	LOG("allDocs(["+ functionNames.join(',') +"]): " + docNames.length + ' docs in ' + app.activeBook.name);
	var docName = docNames.shift();
	while (docName) {
		LOG(docName);
		var docTime = 0;
		$.hiresTimer;
		var doc = app.open(docName, true);	// show the window
		docTime += $.hiresTimer;
		// apply the given function(s) in order
		for (i=0; i < functions.length; i++) {
			var fn = functions[i];
			if (fn) {
				$.hiresTimer;
				docTime += fn(doc, params) || $.hiresTimer;
			}
		}
		$.hiresTimer;
		if (options.close) {
			doc.close(SaveOptions.YES);
		} else if (options.save) {
			doc.save();
		}
		docTime += $.hiresTimer;		
		time += docTime;
		docName = docNames.shift()
		LOG(docTime/1e6 + ' s');
	}
	LOG(time/1e6 + ' s TOTAL');
	return time;
}

