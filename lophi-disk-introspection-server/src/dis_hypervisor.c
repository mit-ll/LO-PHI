/*
 *	(c) 2015 Massachusetts Institute of Technology
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
#include <errno.h>
#include <stdbool.h>
#include <fcntl.h>

#include "disk_introspection_server.h"

#define	MIN(a,b) (((a)<(b))?(a):(b))
#define MAX_SEND_SIZE 1500

// Need a mutex
pthread_mutex_t lophi_cleanup_mutex;

// Struct for passing arguments to threads
typedef struct forward_data_args forward_data_args;
struct forward_data_args {
	void * buffer;
	thread_item * origin_thread;
};

/*
 * This function is spawned as a thread that will simply forward along the
 * content received from the hypervisor instance to our Lo-Phi client asyncronously.
 */
void forward_data(void * buffer, thread_item * thread_data) {
	// Variables
	DiskIntrospectionHeader * header = (DiskIntrospectionHeader *) buffer;
//	void * content = header + sizeof(DiskIntrospectionHeader);
	int packetSize = header->size + sizeof(DiskIntrospectionHeader);

	int written = 0;

	// Loop until the entire buffer is written
	while (written < packetSize) {


		// Write our data to the forward socket (Likely UDP)
		int send_size;
		send_size = MIN(MAX_BYTES_SENT,packetSize-written);

		// Send it
		int w = sendto(thread_data->forward_socket_fd, buffer + written,
				send_size, 0, (struct sockaddr *) &thread_data->forward_client,
				sizeof(thread_data->forward_client));

		// Did the socket close?
		if (w <= 0) {
			lophi_log("LO-PHI Client timed out when forwarding data! (Closing socket)\n");
			//  Shut it down so the client knows we aren't sending anymore data
			shutdown(thread_data->forward_socket_fd,SHUT_RDWR);
			update_forward_fd(thread_data->thread_id, -1, NULL);
			break;
		} else {
			written += w;
		}
	} // End write loop
}

int maxPacket = 0;
int64_t maxPacket1 = 0;
int maxPacket2 = 0;
int maxPacket3 = 0;
int maxPacket4 = 0;
/*
 *	Handles a connection with a guest VM instance
 */
void hypervisor_connection(void * arg) {
	// Get our thread data
	thread_item * thread_data = (thread_item *) arg;
	int newsockfd = thread_data->hypervisor_socket_fd;

	if (VERBOSE)
		printf("new thread %d %d\n", newsockfd, thread_data->thread_id);

	// Init our buffer
	int BUFFER_SIZE = MAX_BYTES_SENT + sizeof(DiskIntrospectionHeader);
	char * buffer = malloc(BUFFER_SIZE);
	int bytes_read;

	// Get our Meta Structure
	DiskIntrospectionMetaStruct * metaData = (DiskIntrospectionMetaStruct *) buffer;

	// Get our meta data
	bytes_read = read(newsockfd, buffer, sizeof(DiskIntrospectionMetaStruct));

	if (bytes_read > 0) {

		// Update our Meta Data
		update_meta_data(thread_data, metaData);

		// Log the connection
		if (VERBOSE)
			printf("Got Meta: %s %d\n", metaData->filename,
					metaData->sector_size);
		lophi_log("Guest VM instance connected.\n");
		fprintf(daemon_logfile, "Filename: %s, Sector Size: %d\n",
				metaData->filename, metaData->sector_size);
		fflush(daemon_logfile);

		// Now that we have our meta-data, see if a client was waiting
		lophi_client * waiting = get_waiting_client(metaData->filename);
		if (waiting != NULL) {
			if (VERBOSE)
				printf("Found waiting client for %s",waiting->img_name);

			// Update our forward socket
			update_forward_fd(thread_data->thread_id,
					waiting->forward_socket_fd, waiting->forward_client);

			// Remove from our list and free memory
			remove_waiting_client(waiting->forward_socket_fd, 1);

		}

		DiskIntrospectionHeader * header = (DiskIntrospectionHeader *) buffer;
//		void * content = buffer + sizeof(DiskIntrospectionHeader);


		// Read data forever
		while ((bytes_read = read(newsockfd, buffer,
				sizeof(DiskIntrospectionHeader))) > 0) {

			// In case we missed any, read it in.
			while (bytes_read < sizeof(DiskIntrospectionHeader))
			{
				bytes_read += read(newsockfd, buffer + bytes_read,
						sizeof(DiskIntrospectionHeader) - bytes_read);
			}
			int packetSize = header->size + sizeof(DiskIntrospectionHeader);

			if (VERBOSE)
				printf("header -> ( %lu,%d,%d,%d ) %d\n", header->sector,
						header->num_sectors, header->op, header->size,
						thread_data->forward_socket_fd);

			if (packetSize > maxPacket) {
				maxPacket = packetSize;
				maxPacket1 = header->sector;
				maxPacket2 = header->size;
				maxPacket3 = header->op;
				maxPacket4 = header->num_sectors;
			}

			// Packet too big?  Just kill this connection
			if (header->size > MAX_BYTES_SENT) {
				lophi_log("Got a packet bigger than our max! /kill self\n");
				printf ("ERROR!!!!! %d > %d\n\n",header->size,MAX_BYTES_SENT);
//				exit(EXIT_FAILURE);
				break;
			}

			// Sanity checks!
			if (header->op != OP_INVALID &&
				header->op != OP_WRITE &&
				header->op != OP_READ) {
				printf("Oh no, bad operation.\n");
				break;
			}

			// See if we got garbage data
			if (header->size%512 != 0) {
				printf("Oh no, bad sector (not divisible by 512)\n");
				break;
			}
			if (header->sector == 0 &&
				header->num_sectors == 0 &&
				header->op == 0 &&
				header->size == 0) {
				printf("Oh no!  All zeros!");
				break;
			}

			// Read the content
			while (bytes_read < packetSize)
			{
				bytes_read += read(newsockfd, buffer + bytes_read,
						packetSize - bytes_read);
			}


			// Check to see if we are forwarding this data or just black-holing it.
			if (thread_data->forward_socket_fd != -1)
				forward_data(buffer,thread_data);

		} // End read loop
	} // end outer if

	// Cleanup our buffer
	free(buffer);

	// If we got here our connection to the hypervisor closed
	pthread_mutex_lock(&lophi_cleanup_mutex);
	if (thread_data->forward_socket_fd >= 0) {
		if (VERBOSE)
			printf("CREATING NEW WAITING CLIENT!");

		// Create a new waiting_client
		create_waiting_client(thread_data->disk_data->filename,
				thread_data->forward_socket_fd, thread_data->forward_client);
		//close(thread_data->forward_socket_fd);
	}
	pthread_mutex_unlock(&lophi_cleanup_mutex);
	if (VERBOSE)
		printf("socket closed.\n");
	// If we got here the socket must have closed
	close(newsockfd);
	remove_thread_item(thread_data);
	pthread_exit(NULL);
}

/*
 *	Starts our thread for the socket server that hypervisor instances will connect to
 */
void start_hypervisor_server(void * args) {
	int sockfd;
	struct sockaddr_un serv_addr, cli_addr;
	socklen_t cli_len;

	// Open a UNIX socket to listen on
	sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (sockfd < 0)
		perror("ERROR opening socket");

	// Setup the server address
	bzero((char *) &serv_addr, sizeof(serv_addr));
	serv_addr.sun_family = AF_UNIX;
	strncpy((char *) &serv_addr.sun_path, LOPHI_DISK_SOCK_ADDRESS,
			sizeof(serv_addr.sun_path));


	// Bind to socket
	unlink(LOPHI_DISK_SOCK_ADDRESS);
	if (bind(sockfd, (struct sockaddr *) &serv_addr, sizeof(struct sockaddr_un))
			< 0)
		perror("ERROR on binding");

	int rcvbuf = 0;
	socklen_t rcvbuf_len = sizeof(rcvbuf);

	// Listen for up to 5 connections at a time
	listen(sockfd, 5);

	// Wait for incoming connections
	cli_len = sizeof(struct sockaddr_un);
	while (1) {
		if (VERBOSE)
			printf("Waiting for new connection...\n");
		fflush(stdout);
		int newsockfd;
		newsockfd = accept(sockfd, (struct sockaddr *) &cli_addr, &cli_len);


		// Make our connection non-blocking
//		fcntl(newsockfd, F_SETFL, O_NONBLOCK);

		// Up our buffer sizes!  We're dealing with big data here
		// 5 1024 sector packets can now be buffered.  (Hopefully this is enough)
		getsockopt(newsockfd, SOL_SOCKET, SO_RCVBUF, (void *)&rcvbuf, &rcvbuf_len);
		if (VERBOSE)
			printf("rb: %d\n",rcvbuf);

		rcvbuf = RECV_BUFFER_SIZE;
		setsockopt(newsockfd, SOL_SOCKET, SO_RCVBUF, (void *)&rcvbuf, rcvbuf_len);
		if (VERBOSE)
			printf("rb: %d\n",rcvbuf);

		getsockopt(newsockfd, SOL_SOCKET, SO_RCVBUF, (void *)&rcvbuf, &rcvbuf_len);
		if (VERBOSE)
			printf("rb: %d\n",rcvbuf);

		if (newsockfd < 0)
			perror("ERROR on accept");

		// insert a new thread into our linked list and spawn a thread to handle the connection
		thread_item * new_thread = create_thread_item();
		new_thread->hypervisor_socket_fd = newsockfd;
		pthread_create(&(new_thread->thread_data), NULL, (void *) hypervisor_connection,
				(void*) new_thread);
		pthread_detach(new_thread->thread_data);
	}

	// Close our socket
	close(sockfd);
}
