
#include "./markup.jsx";
#include "./json/json2.js";

var params = {'a':1, 'b':2};
var img = XML("<img src='MyImage'/>");
notes = tagSelection({
	start: JSON.stringify(params), 
	end: img.toXMLString()
});
