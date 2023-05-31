#target "indesign";
#include "./jasmine/lib/jasmine-core/jasmine.js";
#include "./json/json2.js";
var jasmine = (function () {
	var jasmineRequire = getJasmineRequireObj();
	var jas = jasmineRequire.core(jasmineRequire);
	return jas;
})();
