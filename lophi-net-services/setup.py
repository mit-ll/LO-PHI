"""
    Setup script for LO-PHI Network Services

   (c) 2015 Massachusetts Institute of Technology
"""
import os
from distutils.core import setup

DIR_ROOT = "/opt/lophi"


def get_data_files(rel_dir):
    install_list = []
    for x in os.walk(rel_dir):
        directory = x[0]
        install_files = []

        # Get all the .py files
        for filename in x[2]:
            if not filename.endswith(".pyc"):
                install_files.append(os.path.join(directory, filename))

        if len(install_files) > 0:
            install_path = os.path.join(DIR_ROOT, directory)
            install_list.append((install_path, install_files))

    return install_list


def get_packages(rel_dir):
    packages = [rel_dir]
    for x in os.walk(rel_dir):
        # break into parts
        base = list(os.path.split(x[0]))
        if base[0] == "":
            del base[0]

        for mod_name in x[1]:
            packages.append(".".join(base + [mod_name]))

    return packages


packages = get_packages('lophinet')

data_files = get_data_files("tftpboot")
data_files += get_data_files("conf")
data_files += get_data_files("bin")
data_files += [(os.path.join(DIR_ROOT, 'samba', 'images'), [])]

setup(name='LO-PHI-Net-Services',
      version='1.0',
      description='This contains the LO-PHI Network Services binaries and '
                  'configuration files that includes the following services: '
                  'DNS, DHCP/PXE, TFTP, and a LO-PHI Control service.',
      author='Chad Spensky and Hongyi Hu',
      author_email='lophi@mit.edu',
      packages=packages,
      data_files=data_files
      )
