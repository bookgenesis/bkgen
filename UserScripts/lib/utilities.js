//
//  utilities.js
//
//  Created by Thomas Silkjær on 13/06/14.
//  2K/DENMARK A/S, Denmark – http://2kdenmark.com
//

#include "./config.js";

var shownCheckoutAlert = false;
/*
---------
UTILITIES
---------
*/

function notification(notificationText) {
	// "OS" in $.os on macOS and OS X
	if ($.os.contains("OS")) {
		var notificationScript = File(File($.fileName).parent.fullName + '/macos-notification.scpt').fullName.replace('~', $.getenv('HOME'));
		runShellScript("osascript '"+notificationScript+"' '" + notificationText + "'");		
	}
}

function runShellScript(scriptString) {
	return app.doScript("do shell script \"" + scriptString + "\"", ScriptLanguage.APPLESCRIPT_LANGUAGE);
}

function absoluteURI(uri) {
	return decodeURI(File(uri).absoluteURI).replace(/^~/, $.getenv('HOME'));
}

function normalizePath (str) {										// ensure ASCII, no spaces
	return str.replace(/[^A-Za-z0-9\.\/\-\_]/g, '_');
}

// execute the python script in a manner suitable to the OS / environment
function executePythonScript(scriptPath) {
	if ($.os.indexOf("Windows") > -1) {
		var exePath = scriptPath.replace(".py", ".exe");
		if (File(exePath).exists == true) {
			File(exePath).execute();
		} else {
			File(scriptPath).execute();
		}
	} else {
		var cfg = Config(File($.fileName).parent.fsName+"/__config__.json");
		if ((cfg != null) & (cfg.python_executable != undefined)) {
			py = cfg.python_executable;
		} else {
			py = "python";
		}
		var cmdLine = py + " '" + scriptPath + "'";
		// $.writeln(cmdLine);
		runShellScript(cmdLine);
	}
}

function mergeObjects(objects) {
	var merged = new Object();
	for(var i = 0; i < objects.length; i++) {
		var currentObject = objects[i];
		for (property in currentObject) { 
			merged[property] = currentObject[property];
		}
	}

	return merged;
}

if (!Object.keys) {
	Object.keys = function(obj) {
		var keys = [];
		for (var key in obj) {
			keys.push(key);
		}
		return keys;
	}
}

if (!Object.prototype.keys) {
	Object.prototype.keys = function () {
		var keys = [];
		for (key in this) {
			keys.push(key);
		}
		return keys;
	}
}

// kind(obj) returns the type of the object as a string
function kind(obj) {
	return obj.toString().replace(/^\[+|\]+$/g, '').split(' ')[1];
}

if (!Array.prototype.contains) {
	Array.prototype.contains = function(obj) {
	    for (var i = 0; i < this.length; i++) {
	        if (this[i] === obj) {
	            return true;
	        }
	    }
	    return false;
	}
}

if (!Array.prototype.indexOf) {
	Array.prototype.indexOf = function (searchElement /*, fromIndex */ ) {
		"use strict";
		if (this == null) {
			throw new TypeError();
		}
		var t = Object(this);
		var len = t.length >>> 0;
		if (len === 0) {
			return -1;
		}
		var n = 0;
		if (arguments.length > 1) {
			n = Number(arguments[1]);
			if (n != n) { // shortcut for verifying if it's NaN
				n = 0;
			} else if (n != 0 && n != Infinity && n != -Infinity) {
				n = (n > 0 || -1) * Math.floor(Math.abs(n));
			}
		}
		if (n >= len) {
			return -1;
		}
		var k = n >= 0 ? n : Math.max(len - Math.abs(n), 0);
		for (; k < len; k++) {
			if (k in t && t[k] === searchElement) {
				return k;
			}
		}
		return -1;
	}
}

if (!String.prototype.contains) {
  String.prototype.contains = function(str, startIndex) {
    return ''.indexOf.call(this, str, startIndex) !== -1;
  };
}

function oc(a) {
	var o = {};
	for(var i=0;i<a.length;i++)
	{
		o[a[i]]='';
	}
	return o;
}

function trim(stringToTrim) {
	return stringToTrim.replace(/^\s+|\s+$/gm,"");
}

function ltrim(stringToTrim) {
	return stringToTrim.replace(/^\s+/m,"");
}

function rtrim(stringToTrim) {
	return stringToTrim.replace(/\s+$/m,"");
}

function randomString(length) {
	var chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
	var result = '';
	for (var i = length; i > 0; --i) result += chars[Math.round(Math.random() * (chars.length - 1))];
	return result;
}

function min(arg1, arg2) {
	if (arg1 > arg2) return arg2;
	return arg1;
}

// create the given directory if it doesn't exist
// -- requires shelling out to python
function makeDirs(path) {
	var pythonScript = File($.fileName).parent.fsName+"/mkdirs.py";
	var cfg = Config(File($.fileName).parent.fsName+"/__config__.json");
	$.setenv("WORKFLOW_MAKEDIRS", path);
	executePythonScript(pythonScript);
}

function testSelectable(showAlert) {
	if (typeof(showAlert) == 'undefined') showAlert = true;
	// test to make sure the cursor is in an editable story location.
	if (app.documents.length==0) {
		if (showAlert) alert("A document must be open before editing.");
		return false;
	} else if (app.activeDocument.selection.length == 0) {
		if (showAlert) alert("To edit, please place the cursor into a story.");
		return false;
	} else {
		var textSelection = app.activeDocument.selection[0];
		try {
			var textStory = textSelection.texts[0].parentStory;
		}
		catch (error) {
			if (showAlert) alert("Current selection is not supported (" + textSelection.constructor.name + ").");
			return false;
		}
		var storyLockState = textSelection.texts[0].parentStory.lockState;
		if (storyLockState == LockStateValues.LOCKED_STORY 
			|| storyLockState == LockStateValues.CHECKED_IN_STORY) {
			if (!shownCheckoutAlert) alert("To add or edit index entries, please check out the selected story.");
			shownCheckoutAlert = true;
			return false;
		}
	}
	return true;
}

function testCursorInNote() {
	if (testSelectable()) {
		return kind(app.activeDocument.selection[0].parent)=='Note';
	} else {
		return false;
	}
}

function testCursorInCode(code) {
	if (testCursorInNote()) {
		return app.activeDocument.selection[0].parent.paragraphs[0].contents.indexOf(code) > -1;
	} else {
		return false;
	}
}

function getAnchorDestination(anchor) {
	if (anchor) {
		return app.activeDocument.hyperlinkTextDestinations.itemByName(anchor);
	}
}

function getDestinationPage(destination) {
	if(destination && destination.isValid 
	&& typeof destination.destinationText.parentTextFrames[0] != "undefined") {
		return destination.destinationText.parentTextFrames[0].parentPage;
	}
}
