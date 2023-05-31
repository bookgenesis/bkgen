
var book = app.activeBook;
for (i=0; i < book.bookContents.length; i++) {
	var file = book.bookContents[i].fullName;
	app.open(file, true);	// show the window
}
