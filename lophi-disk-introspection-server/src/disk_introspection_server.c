/*
 * A simple server that accepts clients over TCP and serves raw disk access
 * data from a KVM guest.
 *
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
#include <signal.h>
#include <fcntl.h>
#include <errno.h>



#include "disk_introspection_server.h"
#include "dis_logger.h"

// We need a lock file
const char* lockfile = "/var/lock/disk-introspection-daemon.lock";
const char* pidfile = "/var/lock/disk-introspection-daemon.pid";

// Import functions for our servers
void start_hypervisor_server(void * args);
void start_client_server();
void kill_client_server();
void close_all_thread_sockets();

/*
 * An attempt to shutdown our server gracefully
 */
void terminate_dis(int signo) {
	// TODO: Do something more intelligent
	lophi_log("Shutting down daemon...\n");
	kill_client_server();
	close_all_thread_sockets();
	unlink(LOPHI_DISK_SOCK_ADDRESS);
	exit(0);
}

/*
 * Turn the current process into a daemon
 */
int daemonize() {
	int lfp = -1;
	int pid_fd = -1;
	pid_t pid, sid;
	pid_t running_pid;
	char buffer[1024];


	// Already a daemon
	if (getppid() == 1) {
		return EXIT_SUCCESS;
	}

	// Fork off the parent process
	pid = fork();
	if (pid < 0) {
		exit(EXIT_FAILURE);
	}

	// If we got a good PID then we can exit the parent process
	if (pid > 0) {
		exit(EXIT_SUCCESS);
	}

	// At that point we are the child process

	// Create lock file as the current user to ensure only one daemon
	// at a time
	if (lockfile && lockfile[0]) {
		if ((lfp = open(lockfile, O_RDWR | O_CREAT, 0640)) < 0) {
			lophi_log("Error: Couldn't open lock file.\n");
			exit(EXIT_FAILURE);
		}
		if (lockf(lfp, F_TLOCK, 0) < 0) {
			// Read our pid file
			if ((pid_fd = open(pidfile, O_RDWR | O_CREAT, 0640)) < 0) {
				lophi_log("Error: Couldn't open PID file.\n");
				exit(EXIT_FAILURE);
			}
			read(pid_fd,&running_pid,sizeof(pid_t));
			close(pid_fd);
			// Let them know we can't start
			sprintf(buffer,"Daemon already running (PID: %d)\n",running_pid);
			lophi_log(buffer);
			exit(EXIT_FAILURE);
		}
	}

	// Change the file mode mask to ensure that write to files
	umask(0);

	// Create a new SID for the child process
	sid = setsid();
	if (sid < 0) {
		exit(EXIT_FAILURE);
	}

	// Create our pid file
	if ((pid_fd = open(pidfile, O_RDWR | O_CREAT, 0640)) < 0) {
		lophi_log("Error: Couldn't open PID file.\n");
		exit(EXIT_FAILURE);
	}
	pid = getpid();
	write(pid_fd,&pid,sizeof(pid_t));
	close(pid_fd);

	// Change the working directory.  This prevents the current directory
	// from being locked
	if ((chdir("/")) < 0) {
		exit(EXIT_FAILURE);
	}

	// Redirect standard files to /dev/null
	close(STDIN_FILENO);
	close(STDOUT_FILENO);
	close(STDERR_FILENO);

	return 0;

}

/*
 * Read the PID file and kill a running daemon.
 *
 * return 0 on success -1 on failure
 */
int kill_running_daemon() {
	int pid_fd = -1;
	pid_t running_pid;
	// Read our pid file
	if ((pid_fd = open(pidfile, O_RDWR, 0640)) < 0) {
		lophi_log("Error: Couldn't open PID file.\n");
		return -1;
	}
	read(pid_fd,&running_pid,sizeof(pid_t));
	close(pid_fd);

	if (running_pid == 0)
		return -1;

	// Kill the running process
	printf("Killing running daemon... (PID: %d)\n",running_pid);
	kill(running_pid,SIGTERM);

	// Remove the pid file
	remove(pidfile);

	return 0;
}
/*
 *	Main
 */
int main(int argc, char *argv[]) {

	// Open our log file.
	logger_init();



#if DAEMON
	// Are we shutting down
	if (argc > 1 && strcmp(argv[1],"stop") == 0 ) {
		kill_running_daemon();
		exit(0);
	}
	// Are we restarting?
	if (argc > 1 && strcmp(argv[1],"restart") == 0) {
		kill_running_daemon();
	}

	daemonize();
#endif

	// Register for interrupts
	signal(SIGTERM, terminate_dis);
	signal(SIGHUP, terminate_dis);
	signal(SIGINT, terminate_dis);
	signal(SIGABRT, terminate_dis);
//	signal(SIGSEGV, terminate_dis);

	// Setup our mutex for editing our list of threads on their respective data
	pthread_mutex_init(&thread_list_mutex, NULL);
	pthread_mutex_init(&lophi_mutex, NULL);
	pthread_mutex_init(&lophi_cleanup_mutex, NULL);

	// Start a thread for our hypervisor guests
	pthread_t hypervisor_thread;
	pthread_create(&hypervisor_thread, NULL, (void *) start_hypervisor_server, NULL);
	pthread_detach(hypervisor_thread);

	// Waiting for clients forever
	start_client_server();

	pthread_mutex_destroy(&thread_list_mutex);
	pthread_mutex_destroy(&lophi_mutex);

	return 0;
}
