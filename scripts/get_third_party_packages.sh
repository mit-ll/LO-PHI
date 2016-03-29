cd ..

echo "Getting analyzeMFT..."
cd lophi-analyzeMFT/
git submodule init
git submodule update

echo "Getting QEMU-KVM source..."
apt-get source qemu-kvm=2.0.0
cd qemu-2.0.0+dfsg_patch
./patch_qemu_source.sh ../qemu-2.0.0+dfsg
cd ..

echo "Re-building QEMU-KVM..."
sudo apt-get -y install device-tree-compiler texinfo libaio-dev libasound2-dev libattr1-dev libbrlapi-dev libcap-dev libcap-ng-dev libcurl4-gnutls-dev libfdt-dev libpixman-1-dev libpulse-dev librados-dev librbd-dev libsasl2-dev libsdl1.2-dev libseccomp-dev libspice-server-dev libspice-protocol-dev libusbredirparser-dev libxen-dev uuid-dev xfslibs-dev

cd qemu-2.0.0+dfsg
debuild -uc -us -j

mkdir debian_packages
mv *.deb debian_packages/
mv *.build debian_packages/                                                        
mv *.changes debian_packages/                                                        
mv *.dsc debian_packages/                                                   
mv *.tar.gz debian_packages/                                                        
mv *.xz debian_packages/                                                        

