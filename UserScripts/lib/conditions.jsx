// conditions.jsx: library for working with conditional text
// Sean Harrison <sah@bookgenesis.com>, 2015-07-20

function getConditionsVisibleStates(document) {
	// return an object with condition names and their visibility states
	document = document || app.activeDocument;
	var conditionsVisible = {};
	for (var i=0; i < document.conditions.length; i++) {
		conditionsVisible[document.conditions[i].name] = document.conditions[i].visible;
	}
	return conditionsVisible;
}

function setConditionsVisibleStates(conditionsVisible, document) {
	// set the visibility states of the conditions in the document according to the conditionsVisible parameter
	document = document || app.activeDocument;
	for (var name in conditionsVisible) {
		if (document.conditions.itemByName(name)) {
			document.conditions.itemByName(name).visible = conditionsVisible[name];
		}
	}	
}

function showConditions(namePattern, document) {
	// show the conditions that match namePattern
	document = document || app.activeDocument;
	var condition;
	for (var i=0; i < document.conditions.length; i++) {
		condition = document.conditions[i];
		if (condition.name.search(namePattern) > -1) {
			condition.visible = true;
		}
	}
}

function hideDigitalConditions(document) {
	document = document || app.activeDocument;
	hideConditions(/Digital/i, document);
}

function hideConditions(namePattern, document) {
	// hide the conditions that match namePattern
	document = document || app.activeDocument;
	var condition;
	for (var i=0; i < document.conditions.length; i++) {
		condition = document.conditions[i];
		if (condition.name.search(namePattern) > -1) {
			condition.visible = false;
		}
	}
}

function showAllConditions(document) { showConditions(/.*/g, document); }

function hideAllConditions(document) { hideConditions(/.*/g, document); }

