/*
 * Below are the functions copied verbatim from the Disk Introspection Server
 *
 * This is critical to keep these in sync.  We copied them to remove any
 * build dependencies and in general make the hooks more disjoint from the
 * rest of our framework
 *
 */
#ifndef _LOPHI_DISK_INTROSPECITON_
#define _LOPHI_DISK_INTROSPECTION_


#define DISK_SECTOR_SIZE    512
#define MAX_SECTORS_SENT 1024

#define MAX_BYTES_SENT DISK_SECTOR_SIZE*MAX_SECTORS_SENT

// Socket Stuff
#define LOPHI_DISK_SOCK_ADDRESS	 "/tmp/lophi_disk_socket"

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


/*
 * LO-PHI Function Prototypes for Disk Introspection
 */
int lophi_disk_access(const uint8_t *content, int64_t sector, int num_sectors,
		enum disk_operation op, BlockDriverState *bs);
int lophi_disk_access_iov(QEMUIOVector *qiov, int64_t sector, int num_sectors,
		enum disk_operation op, BlockDriverState *bs);
void lophi_thread(void * args);
bool lophi_init_meta(char * filename);
void lophi_drv_open(BlockDriverState *bs, const char * filename);
int lophi_initialize(void);



#endif




