import sys

def main(args):
    disk = args[0]
    start_sector = int(args[1])
    num_sectors = int(args[2])

    f = open(disk, 'r')
    f.seek(start_sector * 512)
    data = f.read(num_sectors * 512)
    f.close()
    print data.encode('hex')



if __name__=='__main__':
    main(sys.argv[1:])
