# makediskimage.sh

sizeMB=$1
size=$(echo $(($sizeMB*1024*1024/512)))
# set size of disk
echo "1"
sudo dd if=/dev/zero of=usb_${sizeMB}.img bs=512 count=$size
# equivalent to: qemu-img create -f raw harddisk.img 100M
echo "2"
sudo sudo parted -s usb_${sizeMB}.img mktable msdos
# create partition table
echo "3"

sudo parted -s usb_${sizeMB}.img "mkpart p fat32 1 -0"
# make primary partition, type fat32 from 1 to end
echo "4"

sudo parted -s usb_${sizeMB}.img mkfs y 1 fat32
# list partition table (in bytes)
offset=$(parted harddisk.img unit b print | tail -2 | head -1 | cut -f 1 --delimit="B" | cut -c 9-)
echo ""
echo "* Offset: $offset"
echo ""
echo "Done."
# get offset
