
var fs = {
	// return => the relative path to filePath from location
	relPath: function (path, location) {
	    var pathArray = fs.absPath(path).split('/');
	    var locArray = fs.absPath(location).split('/');
	    var relArray = []
	    // Work out how much of the filepath is shared by location and path.
	    var shared = fs.sharedPrefix(path, location);
	    var numParents = locArray.length - shared.length;
	    for (i=0; i < numParents; i++) {
	    	relArray[relArray.length] = '..';
	    }	    	
	    for (i=shared.length; i < pathArray.length; i++) {
	    	relArray[relArray.length] = pathArray[i];
	    }
	    return relArray.join('/');
	},

	absPath: function (path) {
		return decodeURI(File(path).absoluteURI).replace(/^~/, $.getenv('HOME'));
	},

	// return => path elements shared by the two paths
	sharedPrefix: function (path1, path2) {
		path1Array = fs.absPath(path1).split('/');
		path2Array = fs.absPath(path2).split('/');
		var i; 
		var n;
		var shared = Array();
		// use the shorter of the two paths as the limit of comparison
		if (path1Array.length < path2Array.length) { 
			n = path1Array.length;
		} else {
			n = path2Array.length;
		}
		// compare the two paths
		for (i=0; i < n; i++) {
			if (path1Array[i] == path2Array[i]) {
				shared[i] = path1Array[i];
			} else {
				break;
			}
		}
		return shared;
	}
}

// recursively search the path for the given regexp
function findFiles (path, regexp, files) {
	var results = Array();
	files = files || getFilesIn(path);
	for (var i=0; i < files.length; i++) {
		if (files[i].fullName.match(regexp))
			results.push(files[i]);
	}
	return results;
}
	
// collect all the files in a given subfolder, recursively
function getFilesIn(path) {
	var files = Folder(path).getFiles();
	var results = Array();
	for (var i=0; i < files.length; i++) {
		results.push(files[i]);
		if (files[i] instanceof Folder) {
			var subresults = getFilesIn(files[i].fullName);
			for (var j=0; j < subresults.length; j++) 
				results.push(subresults[j]);
		}
	}
	return results;
}