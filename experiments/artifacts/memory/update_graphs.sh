python memory_aggregate_data.py memory_virtual_with_sensor/ memory_virtual_without_sensor/ -t "Memory Performance Comparison (Virtual)" -o memory_virtual.eps
python memory_aggregate_data.py memory_physical_with_sensor/ memory_physical_without_sensor/ -t "Memory Performance Comparison (Physical)" -o memory_physical.eps

scp *.eps 172.25.126.95:~/Papers/lophi_uva/usenix15/figures
