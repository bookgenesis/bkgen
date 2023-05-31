// config.js -- use to load JSON config in given filename into a js object

#include "./json/json2.js";

function Config(fileName) {
	var f = File(fileName); 
	f.open("r"); 
	var t = f.read(); 
	f.close();
    try {
        j = JSON.parse(t);
    } catch(error) {
    	$.writeln(error);
        j = {};
    }
	return j;
}
