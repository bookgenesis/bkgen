/*
Export the activeBook for Digital production.
-- includes creating a book manifest file.
*/

#include "../lib/bookAll.jsx";
#include "../lib/exportDocument.jsx";
#include "../lib/bookManifest.jsx";

// do the export on the documents in the book
bookAll(exportDocument, {exportImages: true, "reopen": false}, {"close": false})
bookManifest();
LOG("finished exporting book " + app.activeBook.name); 
