if (!Object.keys) {
	Object.keys = function(obj) {
		var keys = [];
		for (var key in obj) {
			keys.push(key);
		}
		return keys;
	}
}

if (!Object.prototype.keys) {
	Object.prototype.keys = function () {
		var keys = [];
		for (key in this) {
			keys.push(key);
		}
		return keys;
	}
}

