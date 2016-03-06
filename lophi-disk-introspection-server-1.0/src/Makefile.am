# what flags you want to pass to the C compiler & linker
AM_CFLAGS = --pedantic -Wall -std=gnu99 -O2 -lpthread
AM_LDFLAGS =

bin_PROGRAMS = lophi_disk_introspection_server

lophi_disk_introspection_server_SOURCES = \
   disk_introspection_server.c \
   disk_introspection_server.h \
   dis_client.c \
   dis_threads.c \
   dis_hypervisor.c \
   dis_logger.c
