
#include "./fs.jsx";

// relink images; if they are missing, try to find them based on the document path & link name
// (this is often necessary on macOS when moving files around!)
function relinkImages(doc) {
	doc = doc || app.activeDocument;
	for (i=0; i < doc.links.length; i++) {
		var link = doc.links[i];
		if (!link || link.name.match(/\.(icml|indd|xml)$/)) {
			continue;
		} else if (link.status == LinkStatus.LINK_OUT_OF_DATE) {
			link.update();
		} else if (link.status == (LinkStatus.LINK_MISSING || LinkStatus.LINK_INACCESSIBLE)) {
			var linkName = link.name;
			var docPath = doc.filePath;
			var results = findFiles(docPath, linkName);
			if (results.length > 0) {
				// take the first result
				link.relink(results[0]);
			}
		}
	}
}
