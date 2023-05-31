#include "./json/json2.js";
#include "./logger.js";

function bookManifest(book) {
	book = book || app.activeBook;
	var manifestFile = File(book.filePath.fsName + '/' + book.name.replace(/\.indb/i	, '') + '-manifest.json');
	LOG("manifestFile: " + manifestFile.fsName);
	var manifest = []
	for (var i = 0; i < book.bookContents.length; i++) {
		var contentFile = File(book.bookContents[i].fullName.toString().replace(/\.indd$/, '.idml'));
		// LOG(contentFile);
		manifest.push(contentFile.fsName);
	}
	manifestFile.open('w');
	manifestFile.write(JSON.stringify(manifest, null, 2));
	manifestFile.close();
	return manifestFile;
}
