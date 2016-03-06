"""
    This a nice simple reference implementation when creating quick testing 
    tools for LO-PHI

    (c) 2015 Massachusetts Institute of Technology
"""
# Navtive
import logging
import optparse
import sys
import os

# LO-PHI
import lophi.globals as G
from lophi import command_line

def main(options):
    """
        Implement your function here
    """

    #
    #    DO SOMETHING HERE
    #

if __name__ == "__main__":

    opts = optparse.OptionParser()

    # Add any options we want here
    opts.add_option("-s", "--sample", action="store_true",
        dest="sample", default=False,
        help="Sample")

    # parse user arguments
    command_line.parser(opts, main)
