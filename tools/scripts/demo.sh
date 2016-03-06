cd ..
sudo virt-manager
sudo xterm -geometry 135x25+0+0 -fn 10x20 -title "LO-PHI Server" \
        -fn "-*-courier 10 pitch-medium-r-*-*-*-*-*-*-*-*-*-*" \
        -e /lophi/bin/lophi-controller &
sleep 2
xterm -geometry 135x30+0+1000 -fn 10x20 -title "LO-PHI Console" \
        -fn "-*-courier 10 pitch-medium-r-*-*-*-*-*-*-*-*-*-*" \
        -e /lophi/bin/lophi-master &
