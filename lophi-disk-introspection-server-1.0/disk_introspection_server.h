/*
 *
 */
#ifndef _SERVER_DIS_
#define _SERVER_DIS_
//
//	Meta includes
//
#include "src/dis_comm.h"
#include "src/dis_logger.h"

// Linked-list of thread data
typedef struct thread_item thread_item;

struct thread_item {
	pthread_t thread_data;
	DiskIntrospectionMetaStruct * disk_data;
	int forward_socket_fd;
	struct sockaddr_in * forward_client;
	socklen_t sock_len;
	int hypervisor_socket_fd;
	int thread_id;
	thread_item * next;
	thread_item * prev;
};

typedef struct lophi_client lophi_client;

struct lophi_client {
	char * img_name;
	int forward_socket_fd;
	struct sockaddr_in * forward_client;
	lophi_client * next;
};

extern pthread_mutex_t thread_list_mutex;
extern pthread_mutex_t lophi_mutex;
extern pthread_mutex_t lophi_cleanup_mutex;

// Functions to call into the linked list
extern thread_item * create_thread_item();
extern void remove_thread_item(thread_item * rm_thread);
extern void update_meta_data(thread_item * up_thread, DiskIntrospectionMetaStruct * meta);
extern void update_forward_fd(int thread_id, int forward_fd,
		struct sockaddr_in * cliaddr);
extern int get_vm_id(char * filename);
extern void print_thread_items(int sockfd);
// Lo-Phi Functions
extern lophi_client * create_waiting_client(char * filename, int sock_fd,
		struct sockaddr_in * cliaddr);
extern void remove_waiting_client(int remove_socket_fd, int free_memory);
extern lophi_client * get_waiting_client(char * filename);


extern FILE* daemon_logfile;


// Logging variables
#define DISK_SERVER_LOG	 "/var/log/lophi-disk-introspection-server.log"

// Lo-Phi Variables
#define LOPHI_PORT			31337
#define BIND_RETRY_TIME		15
#define LOPHI_CLIENT_TIMEOUT 10 // Seconds to wait before disconnecting a listening client

// Debug Stuff
#define VERBOSE 0
#define DAEMON 1

#endif
