"""
    LO-PHI's database interface (and extra functions) for tracking binary
    files and analysis jobs

    (c) 2015 Massachusetts Institute of Technology
"""


# Native
import shutil
import random
import string
import os
import errno
import time
import logging
logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G

# LO-PHI Automation
import lophi_automation.database.utils as utils
import lophi_automation.database.documents as documents
import lophi_automation.database.datastore as datastore

        
def sample_doc_id(filepath):
    """
        Returns a sample_doc_id to assign to this sample.
        We can use this to look up the documents for this sample in the database

    """
    return documents.sample_doc_id(
        utils.calculate_combined_hash(filepath))


def tohash(filepath):
    """
        LAMBDA uses SHA-256 to hash its samples as part of the sample doc id
    """
        
    return utils.calculate_sha256(filepath)


def get_sample_path(h):
    """
        Determines the path where the FTP put the sample based on its hash
        This is relative to the FTP root (e.g. G.UPLOAD_FILE_ROOT)
    """
    return os.path.join(h[0], h)



def analysis_doc(sample_doc_id, lophi_command):
    """
        Creates an analysis structure to insert into a sample_doc in the 
        database
        
        TODO: this schema will probably change in the future depending on our
         analysis fields
    """
    rand_num = int(random.random()*10000000000000000)
    return {'_id':documents.DELIMITER.join(['analysis',
                                                           sample_doc_id, 
                                                           str(rand_num)]),
            'created':time.time(),
            'sample': sample_doc_id,
            'submitted_by': lophi_command.submitter,
            'volatility_profile': lophi_command.volatility_profile,
            'analysis_script':lophi_command.analysis,
            'status':G.JOB_QUEUED,
            'machine': "",
            'machine_type': lophi_command.machine_type,
            'output_files':{}
            }


class DatastoreSamples(datastore.Datastore):
    
    """ 
        This is our MongoDB interface for store/retrieving samples
    """

    def __init__(self, db_host=None):
        """
            Intialize our datastore with the proper URI
        """
        uri = 'mongodb://'+db_host+':27017/lophi_db'+G.DB_SAMPLES
        try:
            datastore.Datastore.__init__(self, uri)
        except:
            logger.error("Could not connect to database at %s"%uri)
    
    def _get_random_filename(self):
        """
            Return a random filename so that samples aren't easily identified.
        """
        return ''.join(random.choice(string.ascii_lowercase +
                                     string.ascii_uppercase) for _ in range(
                                     random.randint(10, 20)))
    
    def _get_sample_dir(self,sample_doc_id):
        return os.path.join(G.FTP_ROOT, G.BINARY_FILE_ROOT, sample_doc_id+'_'+str(time.time()))
    
    def copy_sample_to_ftp(self, sample_doc_id, commands=[]):
        """
            Copies sample from database to FTP server temporarily so that
            the SUA can download and run it.
            Automatically generates the lophi.bat file.
            Sample should be deleted eventually after the analysis is complete.
            Returns temp directory <temp> where the sample files are stored
            at G.FTP_ROOT/<temp>/
            
            @param sample_doc_id: The ID of the sample as indexed in the databse
            @param commands: List of commands that should be executed before the 
                    binary. (%sample% will be replaced by the sample filename)
                        
            @return: absolute path where the files were placed
        """
        # generate <temp> name based on sample_doc_id and timestamp
        new_path_dir = self._get_sample_dir(sample_doc_id)
        try:
            os.makedirs(new_path_dir)
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(new_path_dir):
                pass
            else: raise
        
        # need to append exe at the end to make Windows recognize it as
        # executable
        new_path_file = os.path.join(new_path_dir, sample_doc_id+'.exe')
    
        # download the sample from the database and copy it over
        logger.debug("Downloading sample %s to path %s" % (sample_doc_id,
                                                            new_path_file))
        self.download_sample(sample_doc_id, new_path_file)
        
        # create lophi.bat
        logger.debug("Creating file lophi.bat at %s" % new_path_dir)
        f = open(os.path.join(new_path_dir,'lophi.bat'),'w')
        for c in commands:
            c = c.replace('%sample%', sample_doc_id+'.exe')
            f.write(c+'\n')
        # Rename file to something random
        rand_name = self._get_random_filename()
        f.write('move %s.exe %s.exe\n'%(sample_doc_id,rand_name))
        
        # Run file
        f.write(rand_name+'\n')
        f.write('exit\n')
        
        return new_path_dir

    def delete_sample_from_ftp(self, sample_doc_id):
        """
            Cleans up sample from the FTP server, assuming it was put in the
            <dir_path> directory
        """
        rm_dir = self._get_sample_dir(sample_doc_id)
        shutil.rmtree(rm_dir)


class DatastoreAnalysis(datastore.Datastore):
    
    """ 
        This is our datastore for storing LO-PHI analysis results
    """

    def __init__(self, db_host=G.DB_HOST):
        """
            Intialize our datastore with the proper URI
        """
        uri = 'mongodb://'+db_host+':27017/lophi_db'+G.DB_ANALYSES
        
        try:
            datastore.Datastore.__init__(self, uri)
        except:
            logger.error("Could not connect to database at %s"%uri)

    def create_analysis(self, sample_doc_id, lophi_command):
        """
            Create a new analysis entry.  This entry will later be appended
            with files
        
        """
        # Create analysis dict and upload to mongo
        analysis = analysis_doc(sample_doc_id, lophi_command)
        
        self.upload_doc(analysis)
        
        return analysis['_id']

    def append_analysis_file(self, analysis_doc_id, analysis_file_path,
                             analysis_filename):
        """
            Uploads the specified analysis file (e.g. memory dump,
            pcap  file, dcap file, etc.)
            into the G.ANALYSES_COLLECTION and inserts the file's _id into
            the specified field in the specified analysis_doc
        """
        
        if not self.contains_doc(analysis_doc_id):
            logger.error("Database does not have sample id %s" % sample_doc_id)
            return
        
        # Upload the analysis file
        file_id = self.upload_file(analysis_file_path)
        
        # Update the analysis doc    
        analysis_doc = self.download_doc(analysis_doc_id)
        analysis_doc['output_files'][analysis_filename] = file_id

        self.upload_doc(analysis_doc, replace=True)

    def update_analysis_machine(self, analysis_doc_id, machine):
        """
            Update our analysis machine info
        """
        
        if not self.contains_doc(analysis_doc_id):
            logger.error("Database does not have sample id %s" % sample_doc_id)
            return
        
        # Update the analysis doc    
        analysis_doc = self.download_doc(analysis_doc_id)
        analysis_doc['machine'] = machine.config.name
        analysis_doc['machine_type'] = machine.MACHINE_TYPE
    
        # Update database
        self.upload_doc(analysis_doc, replace=True)
        
    def update_analysis(self, analysis_doc_id, parameter, value):
        
        if not self.contains_doc(analysis_doc_id):
            logger.error("Database does not have sample id %s" % sample_doc_id)
            return
        
        # Update the analysis doc    
        analysis_doc = self.download_doc(analysis_doc_id)
        analysis_doc[parameter] = value
        self.upload_doc(analysis_doc, replace=True)