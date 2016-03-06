/*
 * Access guest physical memory via a domain socket.
 *
 * Copyright (C) 2011 Sandia National Laboratories
 * Author: Bryan D. Payne (bdpayne@acm.org)
 */

//#include "cpu-all.h"
#include "qemu-common.h"
#include "exec/cpu-common.h"
#include "exec/cpu-all.h"
#include "config.h"
#include "cpu.h"
#include "qapi-types.h"
#include "linux-headers/linux/kvm.h"

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

#include "lophi-hooks-common.h"
#include "lophi-hooks-memory.h"


struct request{
    uint8_t type;      // 0 quit, 1 read, 2 write, ... rest reserved
    uint64_t address;  // address to read from OR write to
    uint64_t length;   // number of bytes to read OR write
};

/* Retrieve entire CPU state from all CPUs
 * follows CPUX86State structure
 * Only for x86- and x86-64 architectures
 *
 * env is a double pointer because I want it to be an array of env's,
 * each element corresponds to each CPU on the VM
 */

#define MAX_CPUS 32



/*
 *	Used to help with logging.
 */


///* Dumps the state  of all CPUs to a char*
// *
// * TODO: accessors/mutators for each individual field
// */
//static int connection_read_registers (char *ret) {
//	CPUX86State *t;
//
//	int p=0;
//
//	lophi_log("start reading registers\n");
//
//	// serialize the relevant portions of the CPU state (from cpu.h)
//	for (t=first_cpu; t!=NULL; t=t->next_cpu) {
//		int i;
//
//		char buf[512];
//
//	    struct kvm_regs        regs;
//	    struct kvm_sregs       sregs;
//	    struct kvm_debugregs   debug;
//	    struct kvm_msrs        msrs;
//	    struct kvm_fpu         fpu;
//	    struct kvm_lapic_state lapic;
//	    struct kvm_cpuid2      cpuid2;
//
//
//	    int ret_ = 0;
//
//	    ret_ = kvm_vcpu_ioctl(t, KVM_GET_REGS,      &regs);
//	    ret_ = kvm_vcpu_ioctl(t, KVM_GET_SREGS,     &sregs);
//	    ret_ = kvm_vcpu_ioctl(t, KVM_GET_DEBUGREGS, &debug);
//	    ret_ = kvm_vcpu_ioctl(t, KVM_GET_FPU,       &fpu);
//	    ret_ = kvm_vcpu_ioctl(t, KVM_GET_LAPIC,     &lapic);
//
//	    //ret_ = kvm_vcpu_ioctl(t, KVM_GET_CPUID2, &cpuid2);
//	    //ret_ = kvm_vcpu_ioctl(t, KVM_GET_MSRS,   &msrs);
//
//	    sprintf(buf, "regs %lu  sregs %lu  debug %lu  msrs %lu  fpu %lu  lapic %lu  cpuid %lu\n",
//	    		sizeof(struct kvm_regs), sizeof(struct kvm_sregs), sizeof(struct kvm_debugregs),
//	    		sizeof(struct kvm_msrs), sizeof(struct kvm_fpu),   sizeof(struct kvm_lapic_state),
//	    		sizeof(struct kvm_cpuid2) );
//	    lophi_log(buf);
//
//	    memcpy(ret+p, &regs,  sizeof(struct kvm_regs));        p+=sizeof(struct kvm_regs);
//	    memcpy(ret+p, &sregs, sizeof(struct kvm_sregs));       p+=sizeof(struct kvm_sregs);
//	    memcpy(ret+p, &debug, sizeof(struct kvm_debugregs));   p+=sizeof(struct kvm_debugregs);
//	    memcpy(ret+p, &fpu,   sizeof(struct kvm_fpu));         p+=sizeof(struct kvm_fpu);
//	    memcpy(ret+p, &lapic, sizeof(struct kvm_lapic_state)); p+=sizeof(struct kvm_lapic_state);
//	    //memcpy(ret+p, &cpuid2, sizeof(struct kvm_cpuid2));     p+=sizeof(struct kvm_cpuid2);
//	    //memcpy(ret+p, &msrs, sizeof(struct kvm_msrs));         p+=sizeof(struct kvm_msrs);
//
//	    if (t->next_cpu != NULL) {
//	    	sprintf(ret+p, "w00t"); p+=4;  // dumb delimiter
//	    }
//	}
//
//	// number of chars written
//	return p;
//
//}
//
//static uint64_t
//connection_write_registers (char* bufs) {
//	CPUX86State *t;
//	int p=0, ret_;
//
//    struct kvm_regs        regs;
//    struct kvm_sregs       sregs;
//    struct kvm_debugregs   debug;
//    struct kvm_msrs        msrs;
//    struct kvm_fpu         fpu;
//    struct kvm_lapic_state lapic;
//    struct kvm_cpuid2      cpuid2;
//
//    lophi_log("Writing registers\n");
//
//	for (t=first_cpu; t!=NULL; t=t->next_cpu) {
//		memcpy(&regs,  bufs+p, sizeof(struct kvm_regs)); 		p+=sizeof(struct kvm_regs);
//		memcpy(&sregs, bufs+p, sizeof(struct kvm_sregs));		p+=sizeof(struct kvm_sregs);
//		memcpy(&debug, bufs+p, sizeof(struct kvm_debugregs));	p+=sizeof(struct kvm_debugregs);
//		memcpy(&fpu,   bufs+p, sizeof(struct kvm_fpu));			p+=sizeof(struct kvm_fpu);
//		memcpy(&lapic, bufs+p, sizeof(struct kvm_lapic_state));	p+=sizeof(struct kvm_lapic_state);
//
//		lophi_log("Memcpy's done\n");
//
//		ret_ = kvm_vcpu_ioctl(t, KVM_SET_REGS, 		&regs);
//		lophi_log("regs\n");
//	    ret_ = kvm_vcpu_ioctl(t, KVM_SET_SREGS,     &sregs);
//	    lophi_log("sregs\n");
//	    ret_ = kvm_vcpu_ioctl(t, KVM_SET_DEBUGREGS, &debug);
//	    lophi_log("debug regs\n");
//	    ret_ = kvm_vcpu_ioctl(t, KVM_SET_FPU,       &fpu);
//	    lophi_log("fpu regs\n");
//	    ret_ = kvm_vcpu_ioctl(t, KVM_SET_LAPIC,     &lapic);
//	    lophi_log("lapic regs\n");
//	}
//
//	return 1;
//}



static uint64_t
connection_read_memory (uint64_t user_paddr, void *buf, uint64_t user_len)
{
    hwaddr paddr = (hwaddr) user_paddr;
    hwaddr len = (hwaddr) user_len;
    void *guestmem = cpu_physical_memory_map(paddr, &len, 0);
    if (!guestmem){
        return 0;
    }
    memcpy(buf, guestmem, len);
    cpu_physical_memory_unmap(guestmem, len, 0, len);

    return len;
}


static uint64_t
connection_write_memory (uint64_t user_paddr, void *buf, uint64_t user_len)
{
    hwaddr paddr = (hwaddr) user_paddr;
    hwaddr len = (hwaddr) user_len;
    lophi_log("Starting write memory\n");
    void *guestmem = cpu_physical_memory_map(paddr, &len, 1);
    lophi_log("Mapped\n");
    if (!guestmem){
        return 0;
    }
    memcpy(guestmem, buf, len);
    cpu_physical_memory_unmap(guestmem, len, 0, len);
    lophi_log("Unmapped\n");
    return len;
}

static void
send_success_ack (int connection_fd)
{
    uint8_t success = 1;
    int nbytes = write(connection_fd, &success, 1);
    if (1 != nbytes){
        printf("QemuMemoryAccess: failed to send success ack\n");
    }
}

static void
send_fail_ack (int connection_fd)
{
    uint8_t fail = 0;
    int nbytes = write(connection_fd, &fail, 1);
    if (1 != nbytes){
        printf("QemuMemoryAccess: failed to send fail ack\n");
    }
}

static void
connection_handler (int socket_fd, struct sockaddr * address, socklen_t address_length)
{
	int connection_fd;
    int nbytes;
    struct request req;

    connection_fd = accept(socket_fd, (struct sockaddr *) &address, &address_length);

    while (1){
        // client request should match the struct request format
        nbytes = read(connection_fd, &req, sizeof(struct request));

        if (req.type == 0 || nbytes <= 0){
            // request to quit, goodbye

            break;
        }
        else if (nbytes != sizeof(struct request)){
            // error
            continue;
        } else if (req.type == 1){
            // request to read
            char *buf = g_malloc(req.length + 1);
            nbytes = connection_read_memory(req.address, buf, req.length);
            if (nbytes != req.length){
                // read failure, return failure message
                buf[req.length] = 0; // set last byte to 0 for failure
                nbytes = write(connection_fd, buf, 1);
            }
            else{
                // read success, return bytes
                buf[req.length] = 1; // set last byte to 1 for success
                nbytes = write(connection_fd, buf, nbytes + 1);
            }
            g_free(buf);
        }
        else if (req.type == 2){
        	lophi_log("Got write request");
            // request to write
        	char buf[512];
            void *write_buf = g_malloc(req.length);
            lophi_log("Write request\n");
            nbytes = read(connection_fd, write_buf, req.length);

            sprintf(buf, "Read %d bytes from write request\n", nbytes);
            lophi_log(buf);

            if (nbytes != req.length){
                // failed reading the message to write
                send_fail_ack(connection_fd);
            }
            else{
            	lophi_log("Writing %d, ");
                // do the write
                nbytes = connection_write_memory(req.address, write_buf, req.length);
                if (nbytes == req.length){
                    send_success_ack(connection_fd);
                }
                else{
                    send_fail_ack(connection_fd);
                }
            }
            lophi_log("Did stuff");
            g_free(write_buf);
        }
//        else if (req.type == 3) {
//        	//request to read registers
//        	int sz; char *state;
//
//        	state = (char*)g_malloc(MAX_CPUS*2168); // bigger than we need, but whatever
//        	memset(state, 0x00, MAX_CPUS*2168);
//
//        	//void *buf = malloc(req.length);
//        	//nbytes = read(connection_fd, &buf, req.length);
//
//        	// dump all the CPU's states
//        	sz = connection_read_registers(state);
//        	nbytes = write(connection_fd, state, sz);
//        	// the connection_read_registers function mallocs 'state', so we should free it
//        	g_free(state);
//        }
//        else if (req.type == 4) {
//        	lophi_log("Trying to write registers\n");
//        	//request to write registers
//        	int r = 0;
//        	char *state;
//        	state = (char*)g_malloc(MAX_CPUS*2168);
//        	memset(state, 0x00, MAX_CPUS*2168);
//        	r = read(connection_fd, state, MAX_CPUS*2168);
//        	r = connection_write_registers(state);
//        	g_free(state);
//
//        }
        else{
            // unknown command
            printf("QemuMemoryAccess: ignoring unknown command (%d)\n", req.type);
            char *buf = malloc(1);
            buf[0] = 0;
            nbytes = write(connection_fd, buf, 1);
            free(buf);
        }
    }
    close(connection_fd);

}

static void *
memory_access_thread (void *path)
{
    struct sockaddr_un address;
    int socket_fd;
    socklen_t address_length;

    socket_fd = socket(PF_UNIX, SOCK_STREAM, 0);
    if (socket_fd < 0){
        printf("QemuMemoryAccess: socket failed\n");
        goto error_exit;
    }
    unlink(path);
    address.sun_family = AF_UNIX;
    address_length = sizeof(address.sun_family) + sprintf(address.sun_path, "%s", (char *) path);

    if (bind(socket_fd, (struct sockaddr *) &address, address_length) != 0){
        printf("QemuMemoryAccess: bind failed\n");
        goto error_exit;
    }
    if (listen(socket_fd, 0) != 0){
        printf("QemuMemoryAccess: listen failed\n");
        goto error_exit;
    }


    connection_handler(socket_fd, (struct sockaddr *) &address, address_length);

    close(socket_fd);

error_exit:

	unlink(path);
    return NULL;
}

int
memory_access_start (const char *path)
{
    pthread_t thread;
    sigset_t set, oldset;
    int ret;

    // create a copy of path that we can safely use
    char *pathcopy = malloc(strlen(path) + 1);
    memcpy(pathcopy, path, strlen(path) + 1);

    // start the thread
    sigfillset(&set);
    pthread_sigmask(SIG_SETMASK, &set, &oldset);
    ret = pthread_create(&thread, NULL, memory_access_thread, pathcopy);
    pthread_sigmask(SIG_SETMASK, &oldset, NULL);

    return ret;
}

