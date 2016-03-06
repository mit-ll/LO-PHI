#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <signal.h>
#include <stdint.h>
#include <syslog.h>
#include <stdbool.h>

#include "block/block.h"
#include "block/block_int.h"
#include "qemu-common.h"

#include "lophi-hooks-common.h"
#include "lophi-hooks-disk.h"


/*
 *
 * 		LO-PHI Disk Introspection Additions Below
 * -
 * 		These functions will connect to a UNIX socket
 * 		and forward along all disk reads/writes.
 * 		The guest will try to reconnect to the socket after
 * 		LOPHI_RECONNECT_COUNT failed attemps.
 *
 */

// Extracted from pthread.h
/* Mutex initializers.  */
/*
#if __WORDSIZE == 64
# define PTHREAD_MUTEX_INITIALIZER \
  { { 0, 0, 0, 0, 0, 0, { 0, 0 } } }
# ifdef __USE_GNU
#  define PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, 0, PTHREAD_MUTEX_RECURSIVE_NP, 0, { 0, 0 } } }
#  define PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, 0, PTHREAD_MUTEX_ERRORCHECK_NP, 0, { 0, 0 } } }
#  define PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, 0, PTHREAD_MUTEX_ADAPTIVE_NP, 0, { 0, 0 } } }
# endif
#else
# define PTHREAD_MUTEX_INITIALIZER \
  { { 0, 0, 0, 0, 0, { 0 } } }
# ifdef __USE_GNU
#  define PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, PTHREAD_MUTEX_RECURSIVE_NP, 0, { 0 } } }
#  define PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, PTHREAD_MUTEX_ERRORCHECK_NP, 0, { 0 } } }
#  define PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP \
  { { 0, 0, 0, PTHREAD_MUTEX_ADAPTIVE_NP, 0, { 0 } } }
# endif
#endif
*/



/* LOPHI variables */
bool LOPHI_COMM_INIT = false;
bool LOPHI_SOCK_OPEN = false;
int LOPHI_SOCK_FD = -1;
int LOPHI_COUNTER = 0;
int LOPHI_RECONNECT_COUNT = 10;
char * LOPHI_FILENAME = NULL;
BlockDriverState * LOPHI_BLOCK_DEVICE = NULL;
// Mutex to ensure that our list of thread data is thread safe.

pthread_mutex_t socket_thread_mutex = PTHREAD_MUTEX_INITIALIZER;

/* This struct helps pass data to our thread */
struct LOPHIThreadObj {
	uint8_t * content;
	int64_t sector;
	int num_sectors;
	enum disk_operation op;
	BlockDriverState * bs;
};

/*
 * Initialize
 */
int lophi_initialize(void) {

	lophi_log("Initializing...\n");

	// Variables
	struct sockaddr_un serv_addr;
	int len;

	if (LOPHI_SOCK_FD > -1) {
		close(LOPHI_SOCK_FD);
		LOPHI_SOCK_FD = -1;
	}

	// Open socket
	LOPHI_SOCK_FD = socket(AF_UNIX, SOCK_STREAM, 0);
	if (LOPHI_SOCK_FD < 0) {
		lophi_log("ERROR opening socket");
		return -1;
	}
	// Define socket address
	serv_addr.sun_family = AF_UNIX;
	strncpy(serv_addr.sun_path, LOPHI_DISK_SOCK_ADDRESS, sizeof(serv_addr.sun_path));
	len = sizeof(serv_addr.sun_family) + strlen(serv_addr.sun_path);

	// Connect to socket
	if (connect(LOPHI_SOCK_FD, (const struct sockaddr *)&serv_addr, len) < 0) {
		lophi_log("ERROR connecting to socket");
		return -1;
	}

	// Make our connection non-blocking
//	fcntl(DTIM_SOCK_FD, F_SETFL, O_NONBLOCK);

	// Make our send buffer much bigger!
	// 50 1024 sector packets can now be buffered...
	int sendbuff = (MAX_BYTES_SENT+sizeof(DiskIntrospectionHeader))*50;
	setsockopt(LOPHI_SOCK_FD, SOL_SOCKET, SO_SNDBUF, &sendbuff, sizeof(sendbuff));

	// Connected Succesfully
	LOPHI_SOCK_OPEN = true;
	lophi_log("Successfully connected to socket.\n");

	return 0;
}

/*
 * Grab the first non-null filename and save it.  This prevents the driver from
 * eventually replacing it with the backing filename so that we will store the
 * qcow filename for example.
 *
 * Also, detect if we are opening multiple block devices and be sure we only
 * sent read/write info for the highest-level one.
 *
 * Note:  This method is only tested with simple qcow2 drives.  Will likely
 * fail if you try to do something more complex.
 */
void lophi_drv_open(BlockDriverState *bs,const char * filename) {
	// DEBUG STUFF
	char debug_str[2048];
	sprintf(debug_str,"[drv_open] Filename: %s, BS->Filename: %s, Backing HD: %p, Type: ?, Device: %s, BS: %p\n",
			filename,
			bs->filename,
			bs->backing_hd,
//			bs->type,
			bs->device_name,
			bs);
	lophi_log(debug_str);

	// Only set it onces
	if (LOPHI_FILENAME != NULL)
		return;
	// Allocate space and copy our string
	LOPHI_FILENAME = (char *)g_malloc(strlen(filename)+1);
	strncpy(LOPHI_FILENAME,filename,strlen(filename));
	// Terminate the string
	LOPHI_FILENAME[strlen(filename)] = '\0';

	LOPHI_BLOCK_DEVICE = bs;
}
/*
 * This function will send the appropriate meta-data to our server.
 * This meta-data should only be sent once and at the first iteration, this
 * fixed the problem where qcow2 filenames were getting lost because of how
 * Xen maps them.
 *
 */
bool lophi_init_meta(char * filename) {
	int bytes_written = 0;

	lophi_log("Writing meta to socket.");
	// use a struct so that we can expand as needed
	DiskIntrospectionMetaStruct metaStruct;

	// Fill in data
	strncpy(metaStruct.filename, filename,
			sizeof(metaStruct.filename));
	metaStruct.sector_size = BDRV_SECTOR_SIZE;

	// Write meta data to socket
	bytes_written = write(LOPHI_SOCK_FD, &metaStruct,
			sizeof(DiskIntrospectionMetaStruct));
	// Error?
	if (bytes_written < 0) {
		if (LOPHI_COUNTER % LOPHI_RECONNECT_COUNT == 0) {
			lophi_log("ERROR writing meta-data to socket...");
			LOPHI_SOCK_OPEN = LOPHI_COMM_INIT = false;
			lophi_initialize();
			return false;
		}
	} else
		// Communication initialized
		LOPHI_COMM_INIT = true;
	return true;

}

/*
 * Starts a thread to handle our communication with the UNIX socket.
 *   We are trying to interfere with Xen as little as possible.
 */
void lophi_thread(void * args) {
	// Keep this counter to know if we should try to reconnect or not
	LOPHI_COUNTER++;

	// Variables
	struct LOPHIThreadObj * data = (struct LOPHIThreadObj *) args;
	int bytes_written;

	// Make sure we do thread safe writes
	pthread_mutex_lock(&socket_thread_mutex);


	// Have we initalized our communication with meta-data yet?
	if (!LOPHI_COMM_INIT) {
		if (!lophi_init_meta(LOPHI_FILENAME))
			return;
	}
	// This doesn't work because in qcow mode, it redefines the disk to be
	// the original image

	// How much content is there?
	int contentSize = data->num_sectors * BDRV_SECTOR_SIZE;

	// Fill the beginning of our content buffer with our header (space is already reserved)
	DiskIntrospectionHeader * diskAccess = (DiskIntrospectionHeader *) data->content;
	diskAccess->sector = data->sector;
	diskAccess->num_sectors = data->num_sectors;
	diskAccess->op = data->op;
	diskAccess->size = contentSize;

	// Write to socket
	bytes_written = 0;
	while (bytes_written < contentSize + sizeof(DiskIntrospectionHeader)) {
		int w = write(LOPHI_SOCK_FD, data->content+bytes_written,
				contentSize + sizeof(DiskIntrospectionHeader)-bytes_written);
		bytes_written += w;
		if (w <= 0)
			goto error;
	}

	// Are we in an error state?
	error: if (bytes_written < 0) {
		if (LOPHI_COUNTER % LOPHI_RECONNECT_COUNT == 0) {
			lophi_log("ERROR writing to socket...");
			LOPHI_SOCK_OPEN = LOPHI_COMM_INIT = false;
			lophi_initialize();
		}
	}
	pthread_mutex_unlock(&socket_thread_mutex);

	// Free our heap and exit
	g_free(data->content);
	g_free(args);
	pthread_exit(NULL);
}

/**
 * For asyncronous i/o we need to be sure to actually read all of the data from
 * the i/o vector array, we then process the data as before.
 */
int lophi_disk_access_iov(QEMUIOVector *qiov, int64_t sector, int num_sectors,
		enum disk_operation op, BlockDriverState *bs) {

	// Allocate our buffer
	void *buffer = g_malloc(qiov->size);
	int x = 0;
	for (;x< qiov->size;x++) {
		((char *)buffer)[x] = 0x41;
	}

	// Copy the contents into the buffer
	int i = 0;
	int offset = 0;
	for (;i<qiov->niov;i++) {
		memcpy(buffer+offset,qiov->iov[i].iov_base,qiov->iov[i].iov_len);
		offset += qiov->iov[i].iov_len;
	}

	// Send to LO-PHI
	int rtn = lophi_disk_access(buffer, sector, num_sectors, op, bs);

	// Free buffer and return
	g_free(buffer);
	return rtn;

}
/*
 *  Communicate with the traffic investigator by giving it the disk sector and
 *  waiting for a response.
 */
int lophi_disk_access(const uint8_t *content, int64_t sector, int num_sectors,
		enum disk_operation op, BlockDriverState *bs) {

	// Content size?
	int contentSize = num_sectors * BDRV_SECTOR_SIZE;

	if (LOPHI_VERBOSE) {
		openlog ("LOPHI", LOG_CONS | LOG_PID | LOG_NDELAY, LOG_LOCAL1);
		if (op == OP_READ) {
			syslog (LOG_NOTICE, "[READ] Sector: %" PRIu64 ", NumSector: %d, Size: %d", sector, num_sectors,contentSize);
		} else {
			syslog (LOG_NOTICE, "[WRITE] Sector: %" PRIu64 ", NumSector: %d, Size %d", sector, num_sectors, contentSize);
		}
//		int sector = 0;
//		for (;sector<num_sectors;sector++) {
//			char *tmp = g_malloc(BDRV_SECTOR_SIZE*2);
//			int off = 0;
//			for (; off < BDRV_SECTOR_SIZE; off++) {
//				sprintf(tmp+off*2,"%02X",content[sector*BDRV_SECTOR_SIZE+off]);
//			}
//			syslog(LOG_NOTICE, "[SECTOR %d] %s",sector, tmp);
//			g_free(tmp);
//		}
		closelog ();
	}
	// If the socket isn't connected just quit.
	if (!LOPHI_SOCK_OPEN)
		if (LOPHI_COUNTER % LOPHI_RECONNECT_COUNT == 0) {
			lophi_log("ERROR writing to socket...");
			lophi_initialize();
			return 0;
		}

	if (bs != LOPHI_BLOCK_DEVICE) {
		if (LOPHI_VERBOSE) {
			char debug_str[2048];
			sprintf(debug_str,"[Bad Access] BS->Filename: %s, Backing HD: %p, Type: ?, Device: %s, BS: %p\n",
						bs->filename,
						bs->backing_hd,
						bs->device_name,
						bs);
			lophi_log(debug_str);
		}
		return 0;
	}



	// Set our pointers
	struct LOPHIThreadObj * args = (struct LOPHIThreadObj *) g_malloc(
			sizeof(struct LOPHIThreadObj));
	void * buffer = (void *) g_malloc(sizeof(DiskIntrospectionHeader) + contentSize);

	// Copy our content onto the heap, leaving room for the header
	memcpy((void *) (buffer + sizeof(DiskIntrospectionHeader)), (void *) content,
			contentSize);

	// Fill in our arguments
	args->content = buffer;
	args->sector = sector;
	args->num_sectors = num_sectors;
	args->op = op;
	args->bs = bs;

	// Spawn a new thread so we don't hold Xen up anymore
	pthread_t tmp_thread;
	pthread_create(&tmp_thread, NULL, (void *) lophi_thread, args);
	pthread_detach(tmp_thread);

	return 0;
}





