/*
 * File: logger.c
 *
 * Description: Performs basic logging to either the default file or a debug
 * file, either with or without a time/date stamp.
 *
 * (c) 2015 Massachusetts Institute of Technology
 *
 */
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <syslog.h>
#include <string.h>
#include <time.h>
#include <pwd.h>
#include <stdbool.h>
#include <stdint.h>

#include "disk_introspection_server.h"

FILE *log_default;
FILE *log_debug;
const char* default_path = "/var/log/lophi-disk-introspection-server.log";

char log_str[MAX_LOG_STR];


/* Global Variables */
FILE* daemon_logfile = -1;
const char* fname = "/var/log/dtim-daemon.log";

int logger_init(){

	/* Create a log file */
	if ((daemon_logfile = fopen(DISK_SERVER_LOG, "a+")) == NULL) {
		printf("fopen error: %s\n", strerror(errno));
		return EXIT_FAILURE;
	}

   return 0;

}


/*
 * Print a message to the daemon log
 */
int first = 0;
void lophi_log(const char* str)
{
   /* If we haven't initialized, just pipe to stdout */
	if (daemon_logfile == -1) {
		return;
//		daemon_logfile = stdout;
	}

   fprintf(daemon_logfile, "%s", str);
   fflush(daemon_logfile);

   return;
}
