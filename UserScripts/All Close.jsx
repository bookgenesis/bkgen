// all-save.jsx

while (app.documents.length > 0) {
	app.documents[0].close(SaveOptions.ASK);
}