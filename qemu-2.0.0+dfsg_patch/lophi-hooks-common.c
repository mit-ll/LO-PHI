/**
 * Common functions that we want to use accross our instrumentation.
 *
 */

#include <syslog.h>

#include "lophi-hooks-common.h"

/*
 *	Used to help with logging.
 */
void lophi_log(const char* str) {

	openlog ("LOPHI", LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL1);

	syslog (LOG_NOTICE, "%s", str);

	closelog ();

	return;
}
