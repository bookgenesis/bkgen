
#include "./fs.jsx";

var fn = fs.absPath(app.activeDocument.fullName);
var dir = '/Users/sah/python';
alert(fn + "\n" + dir);
alert(fs.relPath(fn, dir));
alert(fs.relPath(fn, fn));
alert(fs.relPath(dir+'/my.py', dir));
