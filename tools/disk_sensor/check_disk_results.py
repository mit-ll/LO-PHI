import os

# dd if=/dev/urandom of=/dev/sdb seek=<sector_number> count=1 bs=512

base_disk = open('/tmp/small.img', 'rb')
managed_disk = open('/tmp/small-tmp.img', 'rb')
orig_disk = open('/tmp/small-base.img', 'rb')

#base_disk = open('/var/lib/libvirt/images/ubuntu-1.img', 'rb')
#managed_disk = open('/tmp/ubuntu-1.img', 'rb')
#orig_disk = open('/tmp/ubuntu-1.img.orig', 'rb')

base_orig_diffs = set(list())
base_managed_diffs = set(list())


#for k in range(os.path.getsize('/var/lib/libvirt/images/ubuntu-1.img')/512):
total = os.path.getsize('/tmp/small.img') / 512
for k in range(total):

    if k % 500000 == 0:
        print "Percent done: ", (k / float(total))

    base_disk.seek(k * 512)
    base_data = base_disk.read(512)

    managed_disk.seek(k * 512)
    managed_data = managed_disk.read(512)

    orig_disk.seek(k * 512)
    orig_data = orig_disk.read(512)

    if (orig_data != base_data):
        #print "Original disk differs from Base disk at sector %d" % k
        #print "Original Data: ", repr(orig_data) 
        #print "Base Data: ", repr(base_data)

        base_orig_diffs.add(k)

    if (orig_data != managed_data):
        #print "Original disk differs from Managed disk at sector %d" % k
        #print "Original Data: ", repr(orig_data) 
        #print "Managed Data: ", repr(managed_data)
        pass

    if (base_data != managed_data):
        #print "Base disk differs from Managed disk at sector %d" % k
        #print "Base Data: ", repr(base_data) 
        #print "Managed Data: ", repr(managed_data)

        base_managed_diffs.add(k)


#print "Different sectors in Original Disk and Base Disk: ", sorted(base_orig_diffs), len(base_orig_diffs)
print "Different sectors in Base Disk and Managed Disk: ", sorted(base_managed_diffs), len(base_managed_diffs)

# Do the sectors line up?
diffs = list(base_orig_diffs - base_managed_diffs)
print "\n"
print "Changed sectors that are not in both: ", sorted(diffs)
#print "Percentage: ", len(diffs)/float(len(base_orig_diffs))

print "Sectors only in base orig diffs: ", base_orig_diffs & set(diffs)
print "Sectors only in base managed diffs: ", base_managed_diffs & set(diffs)

#writes = open('writes.txt', 'r')
#
#write_dict = {}
#
#for line in writes:
#    line2 = line.strip('\n').split(' ', 1)
#    
#    sector = int(line2[0])
#    data = line2[1]
#
#    write_dict[sector] = data


# diffs = []
# managed_write_diffs = []
# orig_write_diffs = []
# orig_managed_diffs = []
# orig_bak_diffs = []
# managed_bak_diffs = []
# out = open('out', 'w')

# for k in write_dict.keys():
#     managed_disk.seek(k*512)
#     managed_data = repr(managed_disk.read(512))

#     orig_disk.seek(k*512)
#     orig_data = repr(orig_disk.read(512))

#     orig_bak.seek(k*512)
#     orig_bak_data = repr(orig_bak.read(512))


#     # check that writes were actually made
#     if managed_data != write_dict[k]:
#         managed_write_diffs.append(k)

#     # check that writes match up with disk
#     if orig_data != write_dict[k]:
#         orig_write_diffs.append(k)
#         out.write(str(k)+'\n')
#         out.write(orig_data+'\n')
#         out.write(write_dict[k]+'\n')


# #    if orig_data != orig_bak_data:
# #        orig_bak_diffs.append(k)

# #    if managed_data != orig_bak_data:
# #        managed_bak_diffs.append(k)

# #    if orig_data != managed_data:
# #        diffs.append(k)


# # check diffs btw base disk and managed disk

# # check diffs btw active disk and managed disk



# print "Managed disk non-matches with writes: ", len(managed_write_diffs)
# print "Orig disk non-matches with writes: ", len(orig_write_diffs)
# print "Total written sectors: ", len(write_dict.keys())
# #print "Total diff sectors between disk and managed disk: ", len(diffs)
# #print "Total diff sectors between orig disk and disk: ", len(orig_bak_diffs)
# #print "Total diff sectors between orig disk and managed: ", len(managed_bak_diffs)
