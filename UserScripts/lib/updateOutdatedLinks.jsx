
function updateOutdatedLinks(doc) {
	doc = doc || app.activeDocument;
	for (var i=0; i < doc.links.length; i++) {
		if (doc.links[i].status == LinkStatus.LINK_OUT_OF_DATE) {
			doc.links[i].update();
		}
	}
}