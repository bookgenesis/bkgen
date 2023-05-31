
#include "./array.js";
#include "./config.js";
#include "./logger.js";
#include "./icml.jsx";

// params -- an object containing parameters for the function(s)
// options -- an object containing options for bookAll

function bookAll(functions, params, options) {
	params = params || {};
	options = options || {'close': true, 'save': true, 'checkout': true};
	if (app.books.length==0) {
		alert("Please open a book and then retry.");
		return;
	}
	// allow the input to be a function or an array of functions
	if (typeof(functions)=='function') {
		var functions = [functions];
	}
	var functionNames = [];
	for (i=0; i < functions.length; i++) functionNames.push(functions[i].name);
	var time = 0;
	var openDocNames = app.documents.everyItem().fullName;
	var docNames = app.activeBook.bookContents.everyItem().fullName;
	LOG("bookAll(["+ functionNames.join(',') +"]): " + docNames.length + ' docs in ' + app.activeBook.name);
	var docName = docNames.shift();
	while (docName) {
		LOG(docName);
		var docTime = 0;
		$.hiresTimer;
		var doc = app.open(docName, true);	// show the window
		if (options.checkout == true) {
			icmlCheckOutStories(doc);
		}
		docTime += $.hiresTimer;
		// apply the given function(s) in order
		for (i=0; i < functions.length; i++) {
			var fn = functions[i];
			if (fn) {
				$.hiresTimer;
				docTime += fn(doc, params) || $.hiresTimer;
			}
		}
		if (options.checkout == true) {
			icmlCheckInStories(doc);
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
	for (var i = 0; i < openDocNames.length; i++) {
		app.open(openDocNames[i], true);
	}
	LOG(time/1e6 + ' s TOTAL');
	return time;
}

