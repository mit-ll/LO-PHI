echo "Disabling dnsmasq..."
sed -i 's/^dns/\#dns/' /etc/NetworkManager/NetworkManager.conf
sudo service network-manager restart

echo "Setting up firewall rules to protect eth0..."
# DHCP
sudo ufw deny in on eth0 to any from any port 68 proto udp
sudo ufw deny in on eth0 to any from any port 69
# DNS
sudo ufw deny in on eth0 to any from any port 53
sudo ufw default allow
sudo ufw enable

echo "Done."
