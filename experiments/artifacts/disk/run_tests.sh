RUNS=50

# Disk virtual
./disk_artifacts.py -T 2 -p WinXPSP3x86 -i virbr0 -m WinXPSP3 -o disk_virtual_with_sensor -S -r $RUNS
./disk_artifacts.py -T 2 -p WinXPSP3x86 -i virbr0 -m WinXPSP3 -o disk_virtual_without_sensor -r $RUNS


# Disk physical
./disk_artifacts.py -T 0 -p WinXPSP3x86 -i eth3 -m Dell -o disk_physical_with_sensor -S -r $RUNS

./disk_artifacts.py -T 0 -p WinXPSP3x86 -i eth3 -m Dell -o disk_physical_without_sensor -r $RUNS


