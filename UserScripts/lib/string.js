if (!String.prototype.contains) {
    String.prototype.contains = function(str, startIndex) {
        return ''.indexOf.call(this, str, startIndex) !== -1;
    };
}

function trim(s) {
    return s.replace(/^\s+|\s+$/gm, "");
}

function ltrim(s) {
    return s.replace(/^\s+/m, "");
}

function rtrim(s) {
    return s.replace(/\s+$/m, "");
}