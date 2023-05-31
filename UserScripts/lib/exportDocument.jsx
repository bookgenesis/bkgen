#include "./pageNumberNotes.jsx";
#include "./conditions.jsx";
#include "./icml.jsx";
#include "./exportImages.jsx";
#include "./logger.js";

function exportDocument(doc, options) {
    doc = doc || app.activeDocument;
    options = options || { exportImages: true, reopen: true };
    if (doc.modified) {
        if (confirm("The document will be saved before exporting. OK?")) {
            doc.save();
        } else {
            return;
        }
    }

    icmlUnlinkStories(doc) // so as not to affect any .icml links
    insertPageNumberNotes(doc);
    if (options.exportImages) {
        exportImages(doc);
    }
    saveAsIDML(doc);

    var docFileName = doc.fullName.fsName;
    doc.close(SaveOptions.NO);
    if (options.reopen != false) {
        doc = app.open(docFileName);
    }
}

function saveAsIDML(doc) {
    showAllConditions(doc);
    doc = doc || app.activeDocument;
    var idmlFile = File(doc.fullName.toString().replace(/\.[^\.]+$/, '.idml'));
    LOG("saveAsIDML: " + idmlFile.fsName);
    doc.exportFile(ExportFormat.INDESIGN_MARKUP, idmlFile.fsName);
}
