"""
    Simple classes that define our commands between masters and controllers

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import json
import uuid

# LO-PHI
import lophi.globals as G

class LophiMessage:
    
    def __init__(self, corr_id=None, data=None):
        self.corr_id = corr_id
        
        if data is not None:
            self.import_str(data)
    
    def export_str(self):
        """
            Return a string representation of our class (e.g. json)
        """
        return json.dumps(self.__dict__)
    
    def import_str(self,json_str):
        """
            Load a string representation of our key/values into our class (e.g. json)
        """
        self.__dict__ = json.loads(json_str)
    
    def __str__(self):
        return self.export_str()
    
    def __len__(self):
        return len(self.__str__())
    
    @classmethod
    def from_data(cls, data):
        lm = cls()
        lm.import_str(data)
        
        return lm
    

class LophiCommand(LophiMessage):
    
    def __init__(self,
                 cmd=None,
                 args=[],
                 controller=None,
                 analysis=None,
                 machine=None,
                 machine_type=None,
                 volatility_profile=None,
                 ftp_ip=None,
                 ftp_dir=None,
                 sample_doc_id=None,
                 db_analysis_id=None,
                 submitter=None,
                 data=None):
        """
            Initialize our variables, convenient for one-liner commands.
        """
        
        # corr_id
        corr_id = str(uuid.uuid4())
        
        self.cmd = cmd
        self.args = args
        self.controller = controller
        self.analysis = analysis
        self.machine = machine
        self.machine_type = machine_type
        self.volatility_profile = volatility_profile
        self.submitter = submitter
        
        self.ftp_info = {'user':G.FTP_USER,
                         'pass':G.FTP_PASSWORD,
                         'ip':ftp_ip,
                         'port':G.FTP_PORT,
                         'dir':ftp_dir
                         }
        self.sample_doc_id = sample_doc_id   # hash name of the exe
        self.db_analysis_id = db_analysis_id
    
        LophiMessage.__init__(self, corr_id=corr_id, data=data)

    def make_response(self, message):
        """
            Create a LophiResponse object from this LophiCommand
            Swaps the routing and reply keys
        """
        return LophiResponse(corr_id=self.corr_id, message=message)
    
    
class LophiResponse(LophiMessage):
    
    def __init__(self, corr_id=None, message=None, data=None):
        
        self.message = message
        
        LophiMessage.__init__(self, corr_id=corr_id, data=data)    
