# Memory virtual
cd memory
sudo ./memory_artifacts.py -m WinXPSP3 -T 2 -p WinXPSP3x86 -i virbr0 -o memory_virtual_with_sensor -S
sudo ./memory_artifacts.py -m WinXPSP3 -T 2 -p WinXPSP3x86 -i virbr0 -o memory_virtual_without_sensor

# Memory physical
./memory_artifacts.py -m Dell -T 0 -p WinXPSP3x86 -i eth3 -o memory_physical_with_sensor -S
./memory_artifacts.py -m Dell -T 0 -p WinXPSP3x86 -i eth3 -o memory_physical_without_sensor
cd ..

cd disk
# Disk virtual
./disk_artifacts.py -T 2 -p WinXPSP3x86 -i virbr0 -m WinXPSP3 -o disk_virtual_with_sensor -S
./disk_artifacts.py -T 2 -p WinXPSP3x86 -i virbr0 -m WinXPSP3 -o disk_virtual_without_sensor

# Disk physical
./disk_artifacts.py -T 0 -p WinXPSP3x86 -i eth3 -m Dell -o disk_physical_with_sensor -S
./disk_artifacts.py -T 0 -p WinXPSP3x86 -i eth3 -m Dell -o disk_physical_without_sensor
cd ..
