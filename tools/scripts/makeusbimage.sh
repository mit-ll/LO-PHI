sizeMB=$1
size=$(echo $(($sizeMB*1024*1024/512)))
# set size of disk
dd if=/dev/zero of=usb_${sizeMB}.img bs=512 count=$size
# equivalent to: qemu-img create -f raw usb_${sizeMB}.img 100M
parted usb_${sizeMB}.img mktable msdos
# create partition table
parted usb_${sizeMB}.img "mkpart p fat32 1 -0"
# make primary partition, type fat32 from 1 to end
parted usb_${sizeMB}.img "mkfs y 1 fat32"
# make fat32 filesystem on partition 1, without confirmation
#parted usb_${sizeMB}.img toggle 1 boot
# make partition 1 bootable
#parted usb_${sizeMB}.img unit b print
# list partition table (in bytes)
offset=$(parted usb_${sizeMB}.img unit b print | tail -2 | head -1 | cut -f 1 --delimit="B" | cut -c 9-)

echo ""
echo "* Offset: $offset"
echo ""
echo "Done."

# get offset
# sometimes 512, 16384 or 35226 (512 bytes per unit by 63 cylinders)
#sudo syslinux -o $offset usb_${sizeMB}.img
# add boot code to partition 1
#dd if=/usr/lib/syslinux/mbr.bin of=usb_${sizeMB}.img conv=notrunc 
# copy master boot record to disk
