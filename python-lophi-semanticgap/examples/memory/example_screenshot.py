"""
    This is an example of using volatility with our sensors to click buttons

    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import optparse
import sys
import logging

logger = logging.getLogger(__name__)

# LO-PHI
import lophi.globals as G
from lophi_semanticgap.memory.volatility_extensions import VolatilityWrapper


def main(options, positionals):
    # Initialize volatility
    vol = VolatilityWrapper(options.target_uri,
                            options.profile,
                            '2147483648')  # 2GB

    print "* Getting screenshot from memory..."
    # get our screenshots
    screenshots = vol.execute_plugin("screenshot")

    # Dump these to files
    idx = 0
    for session in screenshots['HEADER']:
        filename = session + ".png"

        screenshots['DATA'][idx].save(filename, "PNG")
        print "* Saved %s" % filename
        idx += 1


if __name__ == "__main__":

    opts = optparse.OptionParser()

    # Get our machine types
    machine_types = {}
    for x in G.MACHINE_TYPES.__dict__:
        if x != "ASCII" and not x.startswith("_"):
            machine_types[x] = G.MACHINE_TYPES.__dict__[x]

    # Comand line options
    opts.add_option("-l", "--uri", action="store", type="string",
                    dest="target_uri", default=None,
                    help="URI to process.  (E.g. vmi://WinXPSP3, lophi://172.20.1.11, file:///home/blah/image.mfd)")

    opts.add_option("-m", "--memory_sesnor", action="store", type="string",
                    dest="memory_sensor", default=None,
                    help="IP address of physical memory sensor. (Only applicable for physical introspection)")

    opts.add_option("-p", "--profile", action="store", type="string",
                    dest="profile", default="WinXPSP3x86",
                    help="Volatility profile")

    opts.add_option("-d", "--debug", action="store_true",
                    dest="debug", default=False,
                    help="Enable DEBUG")


    # Get arguments
    (options, positionals) = opts.parse_args(None)

    # Get our log level
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()

    # Is a target defined?
    # What sensor type are we initializing?
    if options.target_uri is None:
        logger.error("Please specify a target.")
        opts.print_help()
        sys.exit(0)

    main(options, positionals)
