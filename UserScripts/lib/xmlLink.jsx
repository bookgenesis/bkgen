
function getXMLlink(doc) {
	doc = doc || app.activeDocument;
	for (i=0; i < doc.links.length; i++) {
		var link = doc.links[i];
		if (link.name.match(/\.xml/i)) {
			return link;
		}
	}	
}

function updateXMLlink(doc) {
	doc = doc || app.activeDocument;
	link = getXMLlink(doc);
	if (link.status == LinkStatus.LINK_OUT_OF_DATE) {
		link.update();
	}
}

function unlinkXML(doc) {
	doc = doc || app.activeDocument;
	var link = getXMLlink(doc);
	if (link) {
		link.unlink();
	}
}
