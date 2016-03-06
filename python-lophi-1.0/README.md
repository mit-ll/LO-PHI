# LO-PHI
This repostiory contains a python module for instrumenting both virtual and physical machines, refered to as the system under test (SUT).
The physical instrumentation requires specialized hardware that is not included in this repostitory.
Simiarly, the virtual machine instrumentaiton requires a patched version of Xen or QEMU-KVM and 
the accompanying introspection server.

The general architecture is that a *Machine* has numerous *sensors* by which the code can interact with to perform specific tasks with the machine.
For example, machine.read_memory(address, length) or machine.power_on() would require a memory sensor and control sensor respectively.


LO-PHI currently involves four types of sensors:
 - **Control** handles typical tasks to control input/output (e.g., keyboard, mouse, power)
 - **Memory** enables reading/writing of physical memory of the SUT
 - **Disk** enables passive introspection of low-level disk activity (e.g., sector operations, SATA frames)
 - **Network** enabled basic network capture using a standard NIC

We have done some experiementation with CPU introspection, but have not yet incorporated it into our toolset
 
# Examples

* *sensor_control/*  contains examples of controlling the machines (e.g. keyboard, mouse, power)
* *sensor_disk/* contains examples for capturing data with the disk sensor
* *sensor_memory/* contains examples for reading memory with the memory sensor
* *sensor_network/* contains examples of capturing and replaying network captures

