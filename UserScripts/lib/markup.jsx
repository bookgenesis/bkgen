
// tag the selection with notes at the beginning and end of the selection
// params: {start: content, end: content}
// returns => an object with {start: note, end: note}
function tagSelection(params, document) {
	params = params || {};
	document = document || app.activeDocument;
	restore = {typographersQuotes: typographersQuotesOff(document)};
	var startSel = getSelection(document).insertionPoints.firstItem();
	var endSel = getSelection(document).insertionPoints.lastItem();
	notes = {
		end: insertNote(params.end, endSel, document),
		start: insertNote(params.start, startSel, document)
	};
	restore.typographersQuotes();	
	return notes;
}

// inserts a note at the given insertion point
// returns => the note
function insertNote(content, insertionPoint, document)  {
	document = document || app.activeDocument;
	if (content) {
		insertionPoint = insertionPoint || (selectionEditable() && getSelection().insertionPoints.firstItem());
		var note = insertionPoint.notes.add(LocationOptions.AFTER,insertionPoint,undefined);
		note.insertionPoints.firstItem().contents = content;
		return note;		
	}
}

// saves the state of typographersQuotes for document 
// returns => a function that restores the saved state
function typographersQuotesOff(document) {
	document = document || app.activeDocument;
	var typographersQuotes = document.textPreferences.typographersQuotes;
	var restoreQuotes = function() {
		document.textPreferences.typographersQuotes = typographersQuotes;
	}
	document.textPreferences.typographersQuotes = false;
	return restoreQuotes;
}

// tests whether the selection exists and is editable
function selectionEditable(document) {
	document = document || app.activeDocument;
	var selection = getSelection(document);
	if (!selection) {
		return false; 
	}
	var lock = selection.parentStory.lockState;
	if (lock == LockStateValues.LOCKED_STORY || lock == LockStateValues.CHECKED_IN_STORY) {
		return false;
	}
	return true;
}

// returns => the selection, if there is one.
function getSelection(document) {
	document = document || app.activeDocument;
	if (selectionExists()) {
		return document.selection[0].texts[0];
	}
}

function getSelectionContents(document) {
	var contents = "";
	for (i=0; i < document.selection.length; i++) {
		for (j=0; j < document.selection[i].texts.length; j++) {
			contents += document.selection[i].texts[j].contents || '';
		}
	}
	return contents;
 }

// tests whether a selection exists in the given document
function selectionExists(document) {
	document = document || app.activeDocument;
	if (app.documents.length==0 || !document || document.selection.length==0) {
		return false;
	} 
	try {
		var story = document.selection[0].texts[0].parentStory;
	}
	catch (error) {
		return false;
	}
	return true;
}

// return an array of Notes in the document that matches content
function getNotesMatching(pattern, document) { 
	document = document || app.activeDocument;
	var notes = Array();
	var stories = document.stories.everyItem().getElements();
	for (var i=0; i < stories.length; i++) {
		for (var j=0; j < stories[i].notes.length; j++) {
			var note = stories[i].notes[j];
			if (note.texts.firstItem().contents.match(pattern)) {
				notes[notes.length] = note;
			}
		}
	}
	return notes;
}
