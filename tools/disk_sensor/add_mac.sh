if [ $# -ne 1 ]
then
        echo ""
        echo "Please provide the ethernet interface to add the arp entry too"
        echo ""
        echo "$0 <eth>"
        echo ""
else
        echo "Adding 00:4e:46:32:43:01 -> 172.20.1.1 on $1..."
        sudo arp -i $1 -s 172.20.1.1 00:4e:46:32:43:01
fi

# To delete
# sudo arp -i eth2 -d 172.20.1.1
