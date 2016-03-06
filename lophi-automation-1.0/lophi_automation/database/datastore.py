"""
    Interface to MongoDB

    (c) 2015 Massachusetts Institute of Technology
"""

# LO-PHI Automation
import lophi_automation.database.documents as documents
import lophi_automation.database.mongodb_al as mongodb_al

# Mutex added to avoid a bug when writing large files
from multiprocessing import Lock
MUTEX = Lock()

class Datastore:

    def __init__(self, db_uri):
        self.db = mongodb_al.MongoDb(db_uri)

    def upload_sample(self, file_path):
        file_doc_id = self.db.upload_file(file_path)
        sample_doc = documents.sample_doc(file_path, file_doc_id)
        self.db.upload_dict(sample_doc)

        return sample_doc['_id']

    def download_sample(self, sample_uid, local_path):
        sample_doc = self.db.download_dict(sample_uid)
        self.db.download_file(sample_doc['file_doc_id'], local_path)

    def contains_doc(self, doc_id):
        return self.db.contains_dict(doc_id)

    def upload_doc(self, doc, replace=False):
        with MUTEX:
            if self.db.contains_dict(doc['_id']) and replace:
                self.db.delete_dict(doc['_id'])
            self.db.upload_dict(doc)

    def download_doc(self, doc_id):
        return self.db.download_dict(doc_id)

    def upload_file(self, file_path):
        with MUTEX:
            return self.db.upload_file(file_path)

    def download_file(self, file_doc_id, local_path):
        self.db.download_file(file_doc_id, local_path)

    def reset(self):
        self.db.reset()
