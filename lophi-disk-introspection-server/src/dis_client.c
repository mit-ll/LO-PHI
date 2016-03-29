/*
	(c) 2015 Massachusetts Institute of Technology
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/un.h>
#include <pthread.h>
#include <bits/signum.h>

#include "disk_introspection_server.h"

// Lo-Phi thread argument
typedef struct LoPhiData LoPhiData;
struct LoPhiData {
	int lophi_fd; // socket
	struct sockaddr_in sock_cliaddr;
};
// Socket vars
int LOPHI_SOCKET;
int LOPHI_KILL = 0;
#define BUFFER_LEN 4096

// Mutex to ensure that our list of thread data is thread safe.
pthread_mutex_t lophi_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t lophi_cleanup_mutex = PTHREAD_MUTEX_INITIALIZER;
// Keep track our head and tail
lophi_client * waiting_head = NULL;
lophi_client * waiting_tail = NULL;

/*
 * Will create a new lophi_client struct and place it at the end of our linked-
 * list.  These will then be consummed as Xen instances start to connect.
 */
lophi_client * create_waiting_client(char * filename, int sock_fd,
		struct sockaddr_in * cliaddr) {
	// Allocate our memory
	lophi_client * new_waiting = (lophi_client *) malloc(sizeof(lophi_client));
	new_waiting->forward_socket_fd = sock_fd;
	new_waiting->img_name = (char *) malloc(strlen(filename)+1);
	new_waiting->next = NULL;
	new_waiting->forward_client = (struct sockaddr_in *) malloc(
			sizeof(struct sockaddr_in));

	// Copy data
	strncpy(new_waiting->img_name, filename, strlen(filename)+1);
	memcpy(new_waiting->forward_client, cliaddr, sizeof(struct sockaddr_in));

	pthread_mutex_lock(&lophi_mutex);
	// Insert into linked list
	if (waiting_head == NULL)
		waiting_head = new_waiting;
	if (waiting_tail != NULL)
		waiting_tail->next = new_waiting;

	// Update tail
	waiting_tail = new_waiting;

	pthread_mutex_unlock(&lophi_mutex);

	return new_waiting;
}

/*
 * Will remove the lophi_client struct from our linked list.
 */
void remove_waiting_client(int remove_socket_fd, int free_memory) {
	lophi_client * cur = waiting_head;
	lophi_client * prev = NULL;

	pthread_mutex_lock(&lophi_mutex);
	while (cur != NULL) {
		// Is this the socket that we're removing?
		if (cur->forward_socket_fd == remove_socket_fd) {
			// Update our pointers
			if (prev != NULL)
				prev->next = cur->next;
			if (cur == waiting_head)
				waiting_head = cur->next;
			if (cur == waiting_tail)
				waiting_tail = prev;

			// Iterate
			prev = cur;
			cur = cur->next;

			// Should we free the memory?
			if (free_memory == 1)
				free_waiting_client(prev);
		} else {
			// Keep track of our previous unmatched node
			prev = cur;
			// Iterate
			cur = prev->next;
		}

	}
	pthread_mutex_unlock(&lophi_mutex);
}

/*
 * Will free the memory used by a waiting client object.
 *
 * WARNING: You should ALWAYS within remove_waiting_client.
 */
void free_waiting_client(lophi_client * remove) {
	if (remove->img_name != NULL)
		free(remove->img_name);
	if (remove->forward_client != NULL)
		free(remove->forward_client);
	remove->img_name = remove->forward_client = NULL;
	free(remove);
}

/*
 *	Will return the lophi_client struct accompanied with the given image name.
 */
lophi_client * get_waiting_client(char * filename) {
	lophi_client * cur = waiting_head;
	lophi_client * prev = NULL;
	lophi_client * rtn = NULL;

	pthread_mutex_lock(&lophi_mutex);
	while (cur != NULL) {
		if (strcmp(cur->img_name, filename) == 0)
			rtn = cur;
		cur = cur->next;
	}
	pthread_mutex_unlock(&lophi_mutex);

	return rtn;
}

/*
 *	Will print the list of waiting clients
 */
void print_waiting_clients(int sockfd) {
	lophi_client * cur = waiting_head;
	lophi_client * prev = NULL;
	lophi_client * rtn = NULL;
	char buffer[2048];

	// Header
	snprintf(buffer, sizeof(buffer), " SOCK :  HDD Filename\n" \
									 " ----   ----------------------------------------\n");
	send(sockfd, buffer, strlen(buffer), 0);

	pthread_mutex_lock(&lophi_mutex);
	while (cur != NULL) {

		snprintf(buffer, sizeof(buffer), " %04d : %s\n",
				cur->forward_socket_fd,
				cur->img_name);
		send(sockfd, buffer, strlen(buffer), 0);

		cur = cur->next;
	}
	pthread_mutex_unlock(&lophi_mutex);

}

/*
 *	Will handle an individual connection (thread) from a lo-phi client.
 */
void lophi_connection(void * args) {
	LoPhiData * thread_data = args;

	if (VERBOSE)
		printf("Started lophi thread...\n");

	// Send welcome message
	char * welcome_msg = "LO-PHI Disk Introspection Server\n"
			"Commands\n"
			"   l - list running VM's\n"
			"   i <vm id> - subscribe to VM with specified ID\n"
			"   n <vm filename> - subscribe to VM with specified filename\n";
	//	send(thread_data->lophi_fd, welcome_msg, strlen(welcome_msg), 0);

	// Log it
	lophi_log("LO-PHI Client connected.\n");

	// Loop and retrieve input
	int read_bytes = 0;

	char buffer[BUFFER_LEN] = { 0 }; // Zero the buffer
	lophi_client * waiting_client = NULL;

	// User Input
	int vm_id = -1;
	char filename[BUFFER_LEN] = { 0 };

	// Make sure our sends timeout eventually
	// (Otherwise the Guest threads will backup indefinitely)
	struct timeval timeout;
	timeout.tv_sec = LOPHI_CLIENT_TIMEOUT;
	timeout.tv_usec = 0;
	if (setsockopt (thread_data->lophi_fd, SOL_SOCKET, SO_SNDTIMEO, (char *)&timeout,
				sizeof(timeout)) < 0)
		printf("setsockopt (timeout) failed\n");

	while ((read_bytes = read(thread_data->lophi_fd, buffer, BUFFER_LEN)) > 0) {
		
		fprintf(daemon_logfile,"Got command: %s\n", buffer);
		// List VMs
		if (buffer[0] == 'l')
			print_thread_items(thread_data->lophi_fd);
		if (buffer[0] == 'w')
			print_waiting_clients(thread_data->lophi_fd);
		// Subscribe to a VM stream
		else if (buffer[0] == 'i') {
			char cmd;
			sscanf(buffer, "%c %d", &cmd, &vm_id);
			if (VERBOSE)
				printf("forwarding output for %d\n", cmd, vm_id);
			if (vm_id != -1) {
				update_forward_fd(vm_id, thread_data->lophi_fd,
						&thread_data->sock_cliaddr);
			}
		} else if (buffer[0] == 'n') {

			// Zero our buffer before we read again.
			memset(filename,0,BUFFER_LEN);
			char cmd;

			sscanf(buffer, "%c %[^\t\n]", &cmd, (char *) &filename);//Changed from %s
			fprintf(daemon_logfile, "Testing Filename: %s \n",filename);
			vm_id = get_vm_id(filename);

			// Log the connection
			if (VERBOSE)
				printf("forwarding output for %d(%s)\n", vm_id, filename);

			fprintf(daemon_logfile, "Requested Filename: %s\n", filename);
			fflush(daemon_logfile);


			// Is this Xen image already connected?
			if (vm_id != -1) {
				update_forward_fd(vm_id, thread_data->lophi_fd,
						&thread_data->sock_cliaddr);
			} else {
				// Put this socket in a queue that will be consumed when the
				// Xen image is started
				
				printf("Waiting client...");
				printf("filename: %s",filename);
				waiting_client = create_waiting_client(filename,
						thread_data->lophi_fd, &thread_data->sock_cliaddr);
			}
		} else if (buffer[0] == 'h'){
			send(thread_data->lophi_fd, welcome_msg, strlen(welcome_msg), 0);
		}
		bzero(buffer, BUFFER_LEN); // Zero our buffer
	}

	// If we get here the socket closed.
	pthread_mutex_lock(&lophi_cleanup_mutex);
	if (waiting_client != NULL)
	{
		// Update to remove our forward
		vm_id = get_vm_id(filename);
		printf("Updating forward for %d\n",vm_id);
		if (vm_id != -1)
			update_forward_fd(vm_id, -1, NULL);

		// If this item is still in our linked list, remove it.
		remove_waiting_client(waiting_client->forward_socket_fd, 1);
	}
	pthread_mutex_unlock(&lophi_cleanup_mutex);
	if (VERBOSE)
		printf("Closing lophi thread...\n");
	close(thread_data->lophi_fd);
	free(thread_data);
	pthread_exit(NULL);
}
/*
 *	Starts our LO-PHI Server where LO-PHI clients can connect and subscribe to VM's
 */
void start_client_server() {
	if (VERBOSE)
		printf("Starting LO-PHI Server...\n");

	int connfd;
	struct sockaddr_in servaddr, cliaddr;
	socklen_t clilen;

	// Open our internet socket
	LOPHI_SOCKET = socket(AF_INET, SOCK_STREAM, 0);
	if (LOPHI_SOCKET < 0) {
		perror("ERROR opening inet socket.\n");
		exit(0);
	}

	// Ignore the silly TIME_WAIT state
	int on = 1;
	if (setsockopt(LOPHI_SOCKET, SOL_SOCKET, SO_REUSEADDR, (char *) &on,
			sizeof(on)) < 0)
		perror("Trouble setting socket for reuse");

	// Setup our socket
	bzero(&servaddr, sizeof(servaddr));
	servaddr.sin_family = AF_INET;
	servaddr.sin_addr.s_addr = htonl(INADDR_ANY);
	servaddr.sin_port = htons(LOPHI_PORT);

	// Bind
	while (bind(LOPHI_SOCKET, (struct sockaddr *) &servaddr, sizeof(servaddr))
			< 0) {
		printf("ERROR binding to inet socket... (Retrying in %d seconds)\n",
				BIND_RETRY_TIME);
		sleep(BIND_RETRY_TIME);
	}

	// Listen for 1024 connections
	listen(LOPHI_SOCKET, 1024);

	// Accept clients forever
	if (VERBOSE)
		printf("Waiting for lophi clients on %d...\n", LOPHI_PORT);
	fflush(stdout);
	clilen = sizeof(cliaddr);
	while (!LOPHI_KILL) {
		// Accept new connection
		if ((connfd = accept(LOPHI_SOCKET, (struct sockaddr *) &cliaddr,
				&clilen)) < 0) {
			perror("Lo-Phi Server failed to listen for connections");
			break;
		}
		if (VERBOSE)
			printf("Got connection: %d\n", connfd);

		// Start a new thread
		pthread_t new_thread;
		LoPhiData * data = (LoPhiData *) malloc(sizeof(LoPhiData));
		data->lophi_fd = connfd;
		memcpy(&data->sock_cliaddr, &cliaddr, sizeof(cliaddr));
		pthread_create(&new_thread, NULL, (void *) lophi_connection, data);
		pthread_detach(new_thread);
	}

	fflush(stdout);

}

void kill_client_server() {
	LOPHI_KILL = 1;

	shutdown(LOPHI_SOCKET, 2);
	close(LOPHI_SOCKET);
}
