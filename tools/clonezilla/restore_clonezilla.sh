#!/bin/dash

CYAN="\033[0;36m"

# argument given?
if [ "$#" -ne "1" ]; then
	echo "--"
	echo " syntax: $0 <path to clonezilla image>"
	echo "   e.g.: $0 /lophi/samba/images/winxpsp3"
	echo "--"
	exit
fi

# Script needs to be root
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi


# CD to clonezilla backup directory
cd $1
touch ntfs.img
touch disk.img
chmod 777 ntfs.img
chmod 777 disk.img

##
#  Restore our disk image
##

sudo apt-get -y install partclone > /dev/null

# Restore our NTFS partition
echo "$CYAN* Restoring NTFS partition..."
tput sgr0

# Read all of the paritions and put them back together
parts=`cat parts`
part_imgs=""
echo "$CYAN** Reconstructing $part..."
tput sgr0

for part in $parts;
do
	touch ${part}.img
	chmod 777 ${part}.img
	sudo cat ${part}.ntfs-ptcl-img.gz.* | sudo gzip -c -d | sudo partclone.restore -d -C -s - -O ${part}.img
	part_imgs=$part_imgs+" ${part}.img"
done

# Re-create our actual disk image
echo "$CYAN* Building disk image with MBR... (Grab a coffee)"
tput sgr0

sudo cat sda-mbr sda-hidden-data-after-mbr $part_imgs > disk.img


echo "$CYAN* Done with regeneration of image."
tput sgr0

# Comment if you want the same filesize as the disk!
exit


##
#  Ensure our .img file is the same size as the disk we cloned from
##

# Get the number of sectors on the physical disk (Remove s for sectors)
SECTORS=`cat sda-pt.parted | grep 'Disk' | awk '{print $3}' | tr -d 's'`

# Get the sector size
SECTOR_SIZE_A=`cat sda-pt.parted | grep 'Sector' | awk '{print $4}'`
# Split Logical/Phsical
SECTOR_SIZE_A=(${SECTOR_SIZE_A//\// })
# Remove the B from sector size
SECTOR_SIZE=`echo ${SECTOR_SIZE_A[1]} | tr -d B`

# Calculate our expected size
TOTAL_BYTES=$(($SECTORS*$SECTOR_SIZE))

# Get the actual size of the created image
FILESIZE=$(stat -c%s disk.img)

# Calculate the differnce
PAD_BYTES=$(($TOTAL_BYTES-$FILESIZE))

echo "$CYAN* Re-sizing disk image to match original size... (Padding $PAD_BYTES bytes)"
tput sgr0

# Padd with blocks (Should be faster)
PAD_BYTES=$(($PAD_BYTES/4096))
# Pad our disk image to match the disk it was cloned from
dd if=/dev/zero bs=4096 count=$PAD_BYTES | cat - >> disk.img

##
#  Pad out any odd bytes
##
# Get the actual size of the created image
FILESIZE=$(stat -c%s disk.img)
# Calculate the differnce
PAD_BYTES=$(($TOTAL_BYTES-$FILESIZE))
# Pad our disk image to match the disk it was cloned from
dd if=/dev/zero bs=1 count=$PAD_BYTES | cat - >> disk.img
