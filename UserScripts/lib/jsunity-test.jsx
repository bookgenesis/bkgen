
// if this works, then we can use jsunity as a unit test framework in the current ExtendScript.

#include "./jsunity/assert.js";
#include "./jsunity.jsx";
#include "./json/json2.js";

function testThat() {
    assert.isTrue(true, "true is true");
    assert.isFalse(false, "false is false");
}
JSON.stringify(jsUnity.run([testThat]));
