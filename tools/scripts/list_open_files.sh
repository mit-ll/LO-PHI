sudo lsof -p `ps aux | grep root | grep lophi-controller | awk '{ print $2 }' | tr '\n' ','`

