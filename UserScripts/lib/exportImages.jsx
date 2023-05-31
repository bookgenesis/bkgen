
#include "./fs.jsx";
#include "./markup.jsx";
#include "./logger.js";
#include "./relinkImages.jsx";

var IMAGE_PARAMS = {
	format: ExportFormat.JPG,
	resolution: 600,
	quality: JPEGOptionsQuality.HIGH,
	relPath: ''
}

function exportImages(document, params) {
	document = document || app.activeDocument;
	params = params || {};
	relinkImages(document);
	exportLinkedImages(document, params);
	exportTaggedImages(document, params);
}

// export linked images, and make sure any images referenced in tags are also copied to the export folder
function exportLinkedImages(document, params) {
	params = params || {};
	for (var key in IMAGE_PARAMS) params[key] = params[key] || IMAGE_PARAMS[key]; 
	document = document || app.activeDocument;
	app.jpegExportPreferences.exportResolution = params.resolution;
	app.jpegExportPreferences.jpegQuality = params.quality;
	LOG(document.allGraphics.length + ' graphics in ' + document.fullName.fsName);
	for (var i=0; i < document.allGraphics.length; i++) {
		var image = document.allGraphics[i];
		if (!image.itemLink) { continue; }
		var imageFile = exportImage(image, document, params);
	}
}

// export the given image according to params
function exportImage(image, document, params) {
	params = params || {};
	for (var key in IMAGE_PARAMS) {
		params[key] = params[key] || IMAGE_PARAMS[key]
	}; 
	document = document || app.activeDocument;
	exportFile = File(image.itemLink.filePath);
	if (!image.itemLink.filePath 
		|| (exportFile.parent.fsName.substr(0, document.filePath.fsName.length) 
			!= document.filePath.fsName.substr(0, document.filePath.fsName.length))) {
		exportFile = File(document.filePath.fsName + '/Links/' + exportFile.name);
	} 
	exportFilePath = exportFile.fsName;
	// add page number to filename if it's a multi-page, like PDF or indd.
	try {
		exportFilePath += '-' + image.pdfAttributes.pageNumber;
	} catch (error) {} 
	// only add .jpg if it doesn't already have it
	try {
		if (!exportFilePath.match(/\.jpg$/i)){
			exportFilePath += '.jpg';
		}
	} catch (error) {
		LOG(error);
	}
	// export from the parent so as to get the image as cropped and shown on the page.
	try {
		if (image.parent.exportFile) {
			image.parent.exportFile(ExportFormat.JPG, exportFilePath, false);	
		} else {
			// TODO with images that don't have a parent with an exportFile method?
		}
	} catch (error) {
		LOG(error);
	}
	return exportFilePath;
}

// export tagged images by copying them to the export folder
function exportTaggedImages(document, params) {
	params = params || {};
	for (var key in IMAGE_PARAMS) params[key] = params[key] || IMAGE_PARAMS[key]; 
	document = document || app.activeDocument;
	var exportFolder = params.exportFolder || Folder([document.filePath, params.relPath].join('/'));
	if (!exportFolder.exists) { exportFolder.create(); }
	var imageNotes = getNotesMatching(/^<img/, document);
	for (i=0; i < imageNotes.length; i++) {
		var img = XML(imageNotes[i].texts.firstItem().contents);
		var src = File([document.filePath, img.attribute('src')].join('/'));
		var dest = File([exportFolder.fsName, fs.relPath(src.fsName, document.filePath)].join('/'));
		if (!src.exists) {
			$.writeln("FILE NOT FOUND: " + src.fsName);
		} else {
			if (!dest.parent.exists) { dest.parent.create(); }
			src.copy(dest);
		}
	}
}
