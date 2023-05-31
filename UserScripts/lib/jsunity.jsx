// ------------------------------------------------------------
// jsunity.jsx
// 2016-06-25 by Sean Harrison <sah@blackearth.us>
// 
// This is a _very_ simple wrapper around jsunity 
// for Adobe ExtendScript (= CreativeSuite javascript) 
// so that jsunity.run() can be used to run tests
// ------------------------------------------------------------

#include "./jsunity/jsunity.js";
#include "./jsunity/assert.js";

jsUnity.log.write = function (s) { $.writeln(s); };
jsUnity.log.error = jsUnity.log.write;
