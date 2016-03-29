"""
    Database abstraction layer implementation for MongoDB
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import urlparse
import os
import pymongo
import gridfs

# LO-PHI Automation
import lophi_automation.database.documents as documents

class MongoDb():

    GRIDFS_COLLECTION = 'fs'

    def __init__(self, uri):
        """ A URI initialization string should have the following form:
            http://server:port/dbname[/collection]
        """
        parse_result = urlparse.urlparse(uri)

        self.uri = parse_result.scheme + "://" + parse_result.netloc

        (host, port) = parse_result.netloc.split(':')
        pathelements = parse_result.path[1::] # remove leading '/'
        pathelements = pathelements.split('/')
        if len(pathelements) > 1:
            self.collection_name = pathelements.pop()
            if self.collection_name == '': # trailing '/'
                self.collection_name = 'documents'
        else: # Default collection name
            self.collection_name = 'documents'
        self.database_name = pathelements.pop()
        self.server = pymongo.MongoClient(host, int(port))
        self.database = self.server[self.database_name]
        self.collection = self.database[self.collection_name]
        self.fs = gridfs.GridFS(self.database, self.GRIDFS_COLLECTION)

    def upload_file(self, local_path):
        fname = os.path.split(local_path)[1]
        fid = documents.file_doc_id(local_path)
        try:
            res = self.fs.put(file(local_path), _id=fid, filename=fname)
        except gridfs.errors.FileExists:
            print "WARN: %s was already in the database." % fid

        return fid

    def download_file(self, fid, local_path):
        infile = self.fs.get(fid)
        with open(local_path, 'wb') as outfile:
            outfile.write(infile.read())

    def delete_file(self, fid):
        self.fs.delete(fid)
        return True

    def upload_dict(self, d):
        try:
            self.collection.insert(d)
        except pymongo.errors.DuplicateKeyError:
            print "WARN: %s was already in the database." % d['_id']

    def download_dict(self, did):
        return self.collection.find_one(did)

    def delete_dict(self, did):
        return self.collection.remove(did)

    def contains_dict(self, did):
        return (self.collection.find_one(did) != None)

    def reset(self):
        self.database[self.collection_name].remove()
        self.database[self.GRIDFS_COLLECTION + ".files"].remove()
        self.database[self.GRIDFS_COLLECTION + ".chunks"].remove()

