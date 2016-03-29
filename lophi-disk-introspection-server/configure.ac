#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.68])
AC_INIT([LO-PIH Disk Introspection Server], [1.0], [chad.spensky@ll.mit.edu])
AM_INIT_AUTOMAKE(pippo, 2.6)
AC_CONFIG_SRCDIR([src/dis_threads.c])
AC_CONFIG_HEADERS([config.h])

# Checks for programs.
AC_PROG_CC

# Checks for libraries.

# Checks for header files.
AC_CHECK_HEADERS([fcntl.h netinet/in.h stdlib.h string.h sys/socket.h unistd.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_TYPE_INT32_T
AC_TYPE_INT64_T
AC_TYPE_PID_T
AC_HEADER_STDBOOL
AC_TYPE_UINT8_T

# Checks for library functions.
AC_FUNC_FORK
AC_FUNC_MALLOC
AC_CHECK_FUNCS([bzero memset socket strerror])
AC_CHECK_LIB(pthread, pthread_create,,
  [AC_MSG_ERROR([required library pthread missing])])

AC_CONFIG_FILES([Makefile
                 src/Makefile
                 tools/Makefile])
AC_OUTPUT
