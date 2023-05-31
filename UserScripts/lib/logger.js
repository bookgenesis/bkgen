
#include "./json/json2.js";

var LOG_LEVEL = {
	'DEBUG': 10,
	'INFO': 20,
	'WARN': 30,
	'ERROR': 40,
	'CRITICAL': 50,
};
var CURRENT_LOG_LEVEL = LOG_LEVEL.INFO;

function logger(logFile, loggerLevel) {
	loggerLevel = loggerLevel || CURRENT_LOG_LEVEL;
	// returns a logging function to the given logFile
	if (logFile) {
		logFile.open('a');
	} else {
		logFile = $;
	}
	var log = function (message, logLevel) {
		logLevel = logLevel || CURRENT_LOG_LEVEL;
		if (logLevel >= loggerLevel) {
			try {
				logFile.writeln('[' + Date().toString() + '] ' + message);
			} catch (err) {
				logFile.writeln('[' + Date().toString() + '] ERROR: ' + err.msg);
			}
		}
	};
	log.prototype.close = function () {
		logFile.close();
	}
	return log;
}

var LOG = logger(
	File(
		File($.fileName).parent.parent.fullName			// folder
		+ '/_' 											// put the log at the top of the folder 
		+ File($.fileName).parent.parent.name + '.log' 	// basename
	),
	CURRENT_LOG_LEVEL);
