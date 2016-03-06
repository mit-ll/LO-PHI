RUNS=500

# Memory virtual
sudo ./memory_artifacts.py -m WinXPSP3 -T 2 -p WinXPSP3x86 -i virbr0 -o memory_virtual_with_sensor -S -r $RUNS
sudo ./memory_artifacts.py -m WinXPSP3 -T 2 -p WinXPSP3x86 -i virbr0 -o memory_virtual_without_sensor -r $RUNS

# Memory physical
./memory_artifacts.py -m Dell -T 0 -p WinXPSP3x86 -i eth3 -o memory_physical_with_sensor -S -r $RUNS
./memory_artifacts.py -m Dell -T 0 -p WinXPSP3x86 -i eth3 -o memory_physical_without_sensor -r $RUNS

