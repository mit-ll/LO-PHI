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
#include <stdbool.h>
#include <errno.h>
#include <arpa/inet.h>


#include "disk_introspection_server.h"


int main(int argc, char *argv[]) {
	int sockfd, n;
	struct sockaddr_in serv_addr, cli_addr;
	int len;
	char * buffer = (char *)malloc(MAX_BYTES_SENT);
	char * host = "127.0.0.1";


	printf("\n");


	// Open our socket
	sockfd = socket(AF_INET, SOCK_STREAM, 0);
	if (sockfd < 0) {
		perror("ERROR opening socket");
		exit(-1);
	}

	serv_addr.sin_family = AF_INET;
	serv_addr.sin_port = htons(LOPHI_PORT);
	serv_addr.sin_addr.s_addr = inet_addr(host);


	// TCP?
	if (connect(sockfd, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0) {
		perror("ERROR connecting to lophi-disk-introspection-server (Is it running?)");
		exit(-1);
	}

	int bytes_read;

	// Read the splash screen and display it
//	bytes_read = recv(sockfd, buffer, MAX_BYTES_SENT, 0);
//	if (bytes_read > 0)
//		printf("%s\n", (char *)buffer);

	struct timeval timeout;
	timeout.tv_sec = 1;
	timeout.tv_usec = 0;
	if (setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, (char *) &timeout,
			sizeof(timeout)) < 0)
		perror("Couldn't set timeout");

	printf("Status of connected guest VMs...\n\n");

	sprintf((char *) buffer, "l\n\0");
	sendto(sockfd, buffer, strlen((char *)buffer), 0, (struct sockaddr *)&serv_addr, sizeof(serv_addr));

	while (1) {
		bytes_read = recv(sockfd, buffer, MAX_BYTES_SENT, 0);
		if (bytes_read > 0)
			printf("%.*s", bytes_read, (char *)buffer);
		else
			break;
	}
	printf("\n");

	printf("Status of waiting clients...\n\n");

	sprintf((char *) buffer, "w\n\0");
	sendto(sockfd, buffer, strlen((char *)buffer), 0, (struct sockaddr *)&serv_addr, sizeof(serv_addr));

	while (1) {
		bytes_read = recv(sockfd, buffer, MAX_BYTES_SENT, 0);
		if (bytes_read > 0)
			printf("%.*s", bytes_read, (char *)buffer);
		else
			break;
	}
	printf("\n");

	close(sockfd);
	return 0;
}
