#!/bin/sh
if [ $# -ne 1 ]; then
	echo "Usage: $0 <qemu source directory>"
	exit
fi

# Copy our files into the QEMU-KVM source
cp *.h $1
cp *.c $1
cp *.patch $1
cd $1

# Path the appropriate files
for p in *.patch; do
	echo $p 
	patch < $p
done

# Clean up our patches
rm *.patch

# Commit our patches
dpkg-source --commit

