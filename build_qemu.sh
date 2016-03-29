#!/usr/bin/env bash

dist="qemu-2.0.0+dfsg"

echo "Building QEMU-KVM..."
apt-get source qemu-kvm
chmod 777 *qemu*tar*

cd $dist
debuild --preserve-env clean
dpkg-source --commit
dch -i
yes | debuild --preserve-env -S -kcspensky@cs.ucsb.edu -j4
debuild --preserve-env clean
cd ..

mv *.deb debs/$dist/
mv *.build debs/$dist/
mv *.changes debs/$dist/
mv *.dsc debs/$dist/
mv *.gz debs/$dist/
mv *.xz debs/$dist/
mv *.upload debs/$dist/