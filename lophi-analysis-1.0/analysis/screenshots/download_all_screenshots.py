"""
    Simple program to download all of the screenshots of completed analysis.

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import os

# 3rd Party
from pymongo import MongoClient

# LO-PHI
from lophi_automation.database.mongodb_al import MongoDb


ss_phys = "./ss_phys"
ss_virt = "./ss_virt"

def ensure_dir(d):
    if not os.path.exists(d):
        print "* Creating %s"%d
        os.makedirs(d)
    else:
        print "* %s exists."%d

def download_screenshots(options,positionals):
    """
        Download all of the screenshots from a mongoDB server
    """
    uri = 'mongodb://'+options.services_host+':27017/lophi_db'
    
    print "* Connecting to %s..."%uri
    
    # Initialize our database connections
    client = MongoClient(uri)
    DB = MongoDb(uri)

    ensure_dir(ss_phys)
    ensure_dir(ss_virt)
    
    # Loop over all of our analyses.
    db = client.lophi_db
    analyses = db.analyses
    for analysis in analyses.find():
        
        print analysis['_id']
        if "output_files" in analysis:
            if "screenshot_final" in analysis['output_files']:
                ss_id = analysis['output_files']['screenshot_final']
                print "Downloading %s..."%ss_id
                if analysis['machine_type'] == 2:
                   DB.download_file(ss_id, os.path.join(ss_virt, analysis[
                                                             '_id']+'.ppm'))
                else:
                   DB.download_file(ss_id, os.path.join(ss_phys, analysis[
                                                            '_id']+'.png'))
#            if "memory_dump_dirty" in analysis['output_files']:
#                ss_id = analysis['output_files']['memory_dump_dirty']
#                print "Downloading %s..."%ss_id
#                DB.download_file(ss_id,analysis['_id']+'.tar.gz')


if __name__ == "__main__":
    import optparse
    opts = optparse.OptionParser()
    
    # RabbitMQ (for LARIAT, LAMBDA)
    opts.add_option("-S", "--services_host", action="store", type="string",
                   dest="services_host", default='localhost',
                   help="Host for global services (MongoDB/RabbitMQ)")

    (options, positionals) = opts.parse_args()
    
    download_screenshots(options,positionals)
