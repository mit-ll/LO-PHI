/*
 * This header is used to interface with our hypervisor
 *
 * (c) 2015 Massachusetts Institute of Technology
 */
#ifndef _TRAFFIC_COMM_H_
#define _TRAFFIC_COMM_H_

// Important structs and enums
enum disk_operation {OP_READ, OP_WRITE, OP_INVALID};

typedef struct{
   int32_t seq_id;
   int64_t sector;
   int num_sectors;
   enum disk_operation op;
   uint8_t * data;
}DiskAccessInfo;

// These are socket structures, let's keep them compact.
#pragma pack(push)
#pragma pack(1)

// Used to pass header data over the network to clients
typedef struct{
//   int32_t seq_id;
   int64_t sector;
   int num_sectors;
   enum disk_operation op;
   int32_t size;
} DiskIntrospectionHeader;

// Used to pass meta-data from the hypervisor to the server.  Only a one-time transfer
typedef struct {
	char filename[1024];	// This size is set by the hypervisor.  Keeping it simple.
	int32_t sector_size;
} DiskIntrospectionMetaStruct;
#pragma pack(pop)



#define DISK_SECTOR_SIZE    512
#define MAX_SECTORS_SENT 1024

#define MAX_BYTES_SENT DISK_SECTOR_SIZE*MAX_SECTORS_SENT
#define RECV_BUFFER_SIZE MAX_BYTES_SENT+sizeof(DiskIntrospectionHeader)*2048

// Socket Stuff
#define LOPHI_DISK_SOCK_ADDRESS	 "/tmp/lophi_disk_socket"



#endif

