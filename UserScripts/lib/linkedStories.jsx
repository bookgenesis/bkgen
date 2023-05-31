
function linkedStories(document) {
    document = document || app.activeDocument;
    var stories = Array();
    for (var i = 0; i < document.stories.length; i++) {
        var story = document.stories[i];
        if (story.itemLink) {
            stories.push(story);
        }
    }
    return stories;
}

function checkOutLinkedStories(document) {
    document = document || app.activeDocument;
    var stories = linkedStories(document);
    for (var i = 0; i < stories.length; i++) {
        stories[i].checkOut();
    }
}

function checkInLinkedStories(document) {
    document = document || app.activeDocument;
    document.stories.everyItem().checkIn();
}

function unlinkStories(document, update) {
    document = document || app.activeDocument;
    if (update == null) update = true;
    var stories = linkedStories(document);
    for (i = 0; i < stories.length; i++) {
        var story = stories[i];
        if (story.itemLink) {
            if (story.itemLink.status == LinkStatus.LINK_OUT_OF_DATE && update == true) {
                story.itemLink.update();
            }
            story.itemLink.unlink();
        }
    }
}

function documentHasMissingLinks(document) {
    for (i = 0; i < document.links.length; i++) {
        if (document.links[i].status == LinkStatus.LINK_MISSING ||
            document.links[i].status == LinkStatus.LINK_INACCESSIBLE) {
            return true;
        }
    }
}

// relink stories; if they are missing, try to find them based on the document path & link name
// (this is often necessary on macOS when moving files around!)
function relinkStories(doc) {
    doc = doc || app.activeDocument;
    for (i = 0; i < doc.stories.length; i++) {
        var story = doc.stories[i];
        if (!story.itemLink) {
            continue;
        } else if (story.itemLink.status == LinkStatus.NORMAL) {
        } else if (story.itemLink.status == (
        		LinkStatus.LINK_OUT_OF_DATE 
        		|| LinkStatus.LINK_MISSING 
        		|| LinkStatus.LINK_INACCESSIBLE)) {
            var linkName = story.itemLink.name;
            var docPath = doc.filePath;
            var results = findFiles(docPath, linkName);
            if (results.length > 0) {
                // take the first result
                story.itemLink.relink(results[0]);
            }
        }
    }
}

function updateLinkedStories(doc) {
    doc = doc || app.activeDocument;
    for (i = 0; i < doc.stories.length; i++) {
        var story = doc.stories[i];
        if (story.itemLink && story.itemLink.status == LinkStatus.LINK_OUT_OF_DATE) {
            story.itemLink.update();
        }
    }
}