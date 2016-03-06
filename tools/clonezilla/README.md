# Disk image files

There are numerous issues that may come up when converting from physical to virtual and generally dealing with raw disk images

## Useful tools

  - **testdisk** will test any disk image files for errors etc. and provide useful feedback
  - **libguestfs-tools** also permits manipulation of the image file and has numerous tools 

## Converting Clonezilla disk saves to .img files for virtual machines

Contained are a few scripts to help, but this is still a somewhat manual process.

The overall workflow is as follows:

1. Convert the gz archives back to raw images
> cat sda[NUM].ntfs-ptcl-img.gz.* | sudo gzip -c -d | sudo partclone.restore -d -C -s - -O [image name]

2. Pad these images out to be the sizes denoted in sda-pt.parted
> dd if=/dev/zero bs=4096 count=<BYTES TO PAD> | cat - >> [image name to pad]

3. cat all of the images back together
>  cat sda-mbr sda-hidden-data-after-mbr sda[NUM1] sda[NUM2] > disk.img

4. At this point the disk.img shoudl be a mirror copy of the disk

5. For some windows machines you may need to patch the registry to enable the QEMU drivers.
> sudo virt-win-reg --merge --format raw disk.img MSOFT.reg

## Converting qcow2 to raw

Each machine may have a different configuration.
It's smart to boot the disk with the lophi-controller an ensure that all of the drivers are loaded.
Then take this qcow image, convert it back to raw, and use that as your golden image.

> qemu-img convert -f qcow2 -O raw lophi-0.qcow2 golden.img

# Virtual machiens

## Useful commands

 - Unplug ethernet cable

 > virsh domif-setlink Win7x64-lophi vnet2 down
 
## DHCP after hibernate

 Windows 7 has some issue where it doesn't request a new DHCP lease after sleep/hibernate.
 Unfortuantely the only fix that I found was to **remove** the NIC from the golden image, and let it re-install everytime after the SUT comes out of hibernation.
