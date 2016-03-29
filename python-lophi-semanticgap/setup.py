# Native
import os
from distutils.core import setup, Extension

DIR_ROOT = "/opt/lophi/"


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


data_files = []
# Don't include the examples in the install
# data_files += get_data_files(G.DIR_EXAMPLES)

packages = get_packages('lophi_semanticgap')

setup(name='LOPHI Semantic Gap',
      version='1.0',
      description='Python library that bridges the semantic gap for low level memory, disk, network, etc., data provided by the core LOPHI Python library.',
      author='Chad Spensky and Hongyi Hu',
      author_email='lophi@mit.edu',
      data_files=data_files,
      packages=packages
      )
