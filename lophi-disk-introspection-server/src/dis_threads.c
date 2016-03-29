/*
 * (c) 2015 Massachusetts Institute of Technology
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
#include <stdbool.h>

#include "disk_introspection_server.h"


// Head/Tail of linked-list
thread_item * THREAD_HEAD = NULL;
thread_item * THREAD_TAIL = NULL;

// Mutex to ensure that our list of thread data is thread safe.
pthread_mutex_t thread_list_mutex = PTHREAD_MUTEX_INITIALIZER;

// Unique ID for all of our threads
int cur_thread_id = 0;

/*
 *	Inserts a new thread item in our linked-list and returns a pointer to it.
 */
thread_item * create_thread_item() {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);

	// Create our thread item
	thread_item * new_thread = (thread_item *) malloc(sizeof(thread_item));
	new_thread->next = new_thread->prev = NULL;
	new_thread->disk_data = NULL;
	new_thread->forward_socket_fd = -1;

	// Set a unique id
	new_thread->thread_id = cur_thread_id;
	cur_thread_id++;

	// Will only be true on the first addition
	if (THREAD_HEAD == NULL) {
		THREAD_HEAD = new_thread;
	} else {
		THREAD_TAIL->next = (struct thread_item *) new_thread;
		new_thread->prev = (struct thread_item *) THREAD_TAIL;
	}
	THREAD_TAIL = new_thread;
	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
	return new_thread;
}

/*
 *	Removes a thread item in our linked-list
 */
void remove_thread_item(thread_item * rm_thread) {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);

	// Is it the head or tail?
	if (THREAD_HEAD == rm_thread)
		THREAD_HEAD = rm_thread->next;
	if (THREAD_TAIL == rm_thread)
		THREAD_TAIL = rm_thread->prev;

	// Update pointers
	if (rm_thread->prev != NULL)
		((thread_item *) rm_thread->prev)->next = rm_thread->next;
	if (rm_thread->next != NULL)
		((thread_item *) rm_thread->next)->prev = rm_thread->prev;

	// Free our meta dta
	free(rm_thread->disk_data);

	// Free memory
	free(rm_thread);

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
}

/*
 *	Updates the meta-data of a thread item
 */
void update_meta_data(thread_item * up_thread, DiskIntrospectionMetaStruct * meta) {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);

	DiskIntrospectionMetaStruct * meta_ptr = (DiskIntrospectionMetaStruct *) malloc(
			sizeof(DiskIntrospectionMetaStruct));
	up_thread->disk_data = meta_ptr;
	memcpy(meta_ptr, meta, sizeof(DiskIntrospectionMetaStruct));

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
}

/*
 *	Updates forwarding socket file descriptor
 */
void update_forward_fd(int thread_id, int forward_fd,
		struct sockaddr_in * cliaddr) {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);

	// Update our thread
	thread_item * cur_thread = THREAD_HEAD;
	while (cur_thread != NULL) {
		printf("%d %d\n", cur_thread->thread_id, cur_thread->forward_socket_fd);
		if (cur_thread->thread_id == thread_id) {
			cur_thread->forward_socket_fd = forward_fd;
			if (cliaddr != NULL) {
				cur_thread->forward_client = (struct sockaddr_in *) malloc(
						sizeof(cliaddr));
				memcpy(cur_thread->forward_client, cliaddr, sizeof(cliaddr));
			}
			printf("UPDATED: forward_socket for vm %d -> %d\n", thread_id,forward_fd);
			break;
		}
		cur_thread = cur_thread->next;
	}

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
}

/*
 *	Given a filename, will return the VM ID associated with it.
 *	The VM ID uniquely identifies a thread object.
 */
int get_vm_id(char * filename) {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);
	int id = -1;
	thread_item * cur_thread = THREAD_HEAD;
	while (cur_thread != NULL) {
		if (cur_thread->disk_data != NULL
				&& strcmp(cur_thread->disk_data->filename, filename) == 0) {
			id = cur_thread->thread_id;
			break;
		}
		cur_thread = cur_thread->next;
	}

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);

	return id;
}

/*
 *	Will print the list of connected VM's to a socket
 */
void print_thread_items(int sockfd) {
	// Lock mutex
	pthread_mutex_lock(&thread_list_mutex);

	// Some buffers.
	char buffer[2048];
	char avail[] = "open";
	char used[] = "USED";
	char * status_ptr;

	// Header
	snprintf(buffer, sizeof(buffer), " ID : Status : HDD Filename\n" \
									 " --   ------   ----------------------------------------\n");
	send(sockfd, buffer, strlen(buffer), 0);

	// Walk through the linked list, listing all of the running threads.
	thread_item * cur_thread = THREAD_HEAD;
	while (cur_thread != NULL) {
		if (cur_thread->disk_data == NULL) {
			cur_thread = cur_thread->next;
			continue;
		}

		if (cur_thread->forward_socket_fd == -1)
			status_ptr = avail;
		else
			status_ptr = used;

		snprintf(buffer, sizeof(buffer), "%03d : %06s : %s\n",
				cur_thread->thread_id, status_ptr,
				cur_thread->disk_data->filename);
		send(sockfd, buffer, strlen(buffer), 0);

		cur_thread = cur_thread->next;
	}

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
}

/*
 * This will close all of the open sockets and gracefully close all of our
 * threads.
 */
void close_all_thread_sockets() {
	pthread_mutex_lock(&thread_list_mutex);
	thread_item * cur_thread = THREAD_HEAD;
	while (cur_thread != NULL) {
		if (cur_thread->hypervisor_socket_fd != -1) {
			close(cur_thread->hypervisor_socket_fd);
			cur_thread->hypervisor_socket_fd = -1;
		}
		if (cur_thread->forward_socket_fd != -1) {
			close(cur_thread->forward_socket_fd);
			cur_thread->forward_socket_fd = -1;
		}
		cur_thread = cur_thread->next;
	}

	// Unlock mutex
	pthread_mutex_unlock(&thread_list_mutex);
}
