#!/usr/bin/env bash
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

echo "Adding LO-PHI PPA to APT..."
sudo add-apt-repository ppa:cspensky/lophi
sudo apt-get update

echo "Giving LO-PHI repository priority..."
echo """
Package: *
Pin: release o=LP-PPA-cspensky-lophi
Pin-Priority: 600
""" > /etc/apt/preferences.d/lophi-prefs-600

echo "Updating APT..."
# Update APT
sudo apt-get update
