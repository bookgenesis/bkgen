
function makeDocumentArticle(doc) {
	doc = doc || app.activeDocument;
	while (doc.articles.length > 0) {
		doc.articles[0].remove();
	}
	var article = doc.articles.add('1');
	article.addDocumentContent();
}
