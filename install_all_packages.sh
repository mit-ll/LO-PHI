#!/usr/bin/env bash
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

scriptPath=$(dirname $0)
cd $scriptPath

./scripts/setup_apt_ppa.sh

# Install LO-PHI packages
echo "Installing LO-PHI packages..."
sudo apt-get install --force-yes -y python-lophi
sudo apt-get install --force-yes -y python-lophi-analyzemft
sudo apt-get install --force-yes -y python-lophi-semanticgap
sudo apt-get install --force-yes -y python-lophi-volatility
sudo apt-get install --force-yes -y lophi-automation
sudo apt-get install --force-yes -y lophi-disk-introspection-server
sudo apt-get install --force-yes -y lophi-net-services

# Install KVM
echo "Installing QEMU-KVM..."
sudo apt-get install --force-yes -y --reinstall qemu-kvm

echo "Holding QEMU-KVM package"
sudo apt-mark hold qemu-kvm

echo "Fixing QEMU-KVM installl..."
./scripts/fix_kvm_install.sh