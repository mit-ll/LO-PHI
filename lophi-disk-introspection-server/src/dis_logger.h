/*
 * (c) 2015 Massachusetts Institute of Technology
 */

#ifndef _LOGGER_H_
#define _LOGGER_H_

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_LOG_STR 1024

extern const char* default_path;
extern char log_str[MAX_LOG_STR];

int logger_init(void);
void lophi_log(const char* str);
void daemon_log_short(const char* str);

#ifdef __cplusplus
}
#endif

#endif

