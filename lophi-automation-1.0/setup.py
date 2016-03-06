"""
    Setup script for LO-PHI Automation

    (c) 2015 Massachusetts Institute of Technology
"""
# Native
import os
from distutils.core import setup, Extension

import lophi.globals as G

def get_packages(rel_dir):
    
    packages = [rel_dir]
    for x in os.walk(rel_dir):
        # break into parts
        base = list(os.path.split(x[0]))
        if base[0] == "":
            del base[0]
        
        for mod_name in x[1]:
            packages.append( ".".join(base + [mod_name]) )
            
    return packages
            

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
            install_path = os.path.join(G.DIR_ROOT,directory)
            install_list.append( (install_path, install_files) )

    return install_list

        
data_files = []
data_files += get_data_files(G.DIR_ACTUATION_SCRIPTS)
data_files += get_data_files(G.DIR_ANALYSIS_SCRIPTS)
data_files += get_data_files("bin")
data_files += get_data_files("conf")

# Create empty directories for tmp files and disk scans
data_files += [(os.path.join("/lophi","disk_scans"), [])]
data_files += [(os.path.join("/lophi","disk_images"), [])]
data_files += [(os.path.join("/lophi","tmp"), [])]
data_files += [(os.path.join("/lophi","vms"), [])]

packages = get_packages('lophi_automation')

setup (name = 'LO-PHI Automation',
        version = '1.0',
        description = 'This is the Python library that handles automating LOPHI at scale, e.g., master and controller libs.',
        author = 'Chad Spensky and Hongyi Hu',
        author_email = 'chad.spensky@ll.mit.edu, hongyi.hu@ll.mit.edu',
        data_files = data_files,
        packages = packages
)
