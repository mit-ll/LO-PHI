MACHINE_TYPE=$1

[ "$#" -eq 1 ] || die "Usage: $0 <machine_type>"

mkdir /tmp/lophi-tmp-mem
sudo mount -t tmpfs -osize=15G tmpfs /tmp/lophi-tmp-mem
python memory/memory_analysis.py -a -d
sudo umount /tmp/lophi-tmp-mem


mkdir filters
python memory/make_filter_memory.py -T ${MACHINE_TYPE} -a malware -p Win7SP0x64 -i sample_94f7757a2487b7bebb9cc0d4547c82ad -o filters/filter_${MACHINE_TYPE}_mem  -d
python memory/apply_filter_memory.py -T ${MACHINE_TYPE} -a malware -p Win7SP0x64 -f filters/filter_${MACHINE_TYPE}_mem/filter.mem


python network/network_analysis.py -a



#python get_analyses.py -T 0 -o filter_phys -i sample_94f7757a2487b7bebb9cc0d4547c82ad
#python memory/make_filter_memory.py --dir=filter_phys/ -o filter_phys/filter --profile=Win7SP0x64 -d -r


