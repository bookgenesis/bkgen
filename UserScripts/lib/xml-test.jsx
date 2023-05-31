
var note = app.activeDocument.stories[0].notes[0];
note.insertLabel('hello', 'seanharrison');
var s = note.texts.item(0).contents;
alert(s);
var x = XML(s);
alert(x.attribute('class') + '\n' + x.text()[0] + '\nhello=' + note.extractLabel('hello'));