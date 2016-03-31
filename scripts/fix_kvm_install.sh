#!/usr/bin/env bash
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi


if grep -q "LO-PHI" /etc/apparmor.d/abstractions/libvirt-qemu
then
        echo "Exemption already found."
else
        echo "Adding AppArmor exception for /tmp for libvmi..."
        echo "
  # LO-PHI: Permits libvirt to open a unix socket for memory/disk accesses.
  /tmp/* rw,
">> /etc/apparmor.d/abstractions/libvirt-qemu
fi

# Fix our permissions for libvirt
sed -i 's/unix_sock_rw_perms = .*/unix_sock_rw_perms = "0777"/' /etc/libvirt/libvirtd.conf

sed -i "s/.*max_clients.*/max_clients = 500/" /etc/libvirt/libvirtd.conf 


service libvirt-bin restart
