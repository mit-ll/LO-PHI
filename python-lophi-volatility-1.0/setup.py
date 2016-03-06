import os
from distutils.core import setup

def get_data_files(rel_dir):
    
    install_list = []
    for x in os.walk(rel_dir):
        directory = x[0]
        install_files = []
        
        # Get all the .py files
        for filename in x[2]:
            if not filename.endswith(".pyc"):
                install_files.append( os.path.join(directory, filename) )
        
        if len(install_files) > 0:
            install_path = os.path.join("/lophi",directory)
            install_list.append( (install_path, install_files) )
        
    
    return install_list

data_files = get_data_files("volatility")
data_files += get_data_files("pypi")

setup (name = 'LOPHI-Volatility',
        version = '1.0',
        description = 'This package will download Volatility and all of its dependencies.  It will additionaly patch it to work properly LO-PHI.',
        author = 'Chad Spensky and Hongyi Hu',
        author_email = 'chad.spensky@ll.mit.edu, hongyi.hu@ll.mit.edu',
        data_files = data_files
)

