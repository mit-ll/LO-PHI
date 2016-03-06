"""
    Very simple process to display graphs of multiple LO-PHI machines outputs.
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Threading
import multiprocessing
import Queue # For Empty exception
import sys

# Lo-Phi
import lophi.globals as G

START_IDX = 0

class LoPhiGrapher(multiprocessing.Process):
    """
        This class will continuously read in data from a queue and display 
        live-updating graphs.
    """
    GRAPH_LISTS = ['pslist']#,'modules']



    def __init__(self, data_queue):
        """
            Initialize our variables
        """

        # Init our mapping
        self.int_mapping_cnt = {}
        self.int_mapping = {}

        # Remember our input queue
        self.DATA_QUEUE = data_queue

        # Init our data dict
        self.graph_data = {}

        multiprocessing.Process.__init__(self)


    def str_to_int(self, list_name, a):
        """ 
            Simple function to map strings to integers
        """
        # Create a new mapping list
        if list_name not in self.int_mapping:
            self.int_mapping[list_name] = {}
            self.int_mapping_cnt[list_name] = START_IDX

        if a not in self.int_mapping[list_name]:
            self.int_mapping[list_name][a] = self.int_mapping_cnt[list_name]
            self.int_mapping_cnt[list_name] += 1
        return self.int_mapping[list_name][a]


    def int_to_str(self, list_name, i):
        """ 
            Given our string to integer mapping, will return the string 
            associated with a particular int 
        """
        rtn = [k for k, v in self.int_mapping[list_name].iteritems() if v == i]
        if len(rtn) == 0:
            return None
        else:
            return rtn[0]

    def update_graph(self):
        """
            Will take our internal data structures and draw the appropriate 
            graphs
        """
        # Modules are nice
        import numpy as np

        # Clear our figure
        self.fig.clear()
        idx = 0

        # Draw 1 histogram for each type of data that we are monitoring
        for m in self.graph_data:
            # setup our subplot
            ax = self.fig.add_subplot(1, len(self.graph_data.keys()), idx)
            ax.tick_params(labelsize='small')
            idx += 1

            # Labeling and limits
            ax.set_xlabel('Count')
            ax.set_ylabel(m)
            ax.set_title('Histogram of %s' % (m))
            ax.set_ylim(0, len(self.int_mapping[m]))
            ticks = [self.int_to_str(m, x) for x in range(len(self.int_mapping[m]))]
            self.plt.yticks([x + .5 for x in range(len(self.int_mapping[m]))], ticks)

            # Now put our data in bins and plot it
            data = []
            for name in self.graph_data[m]:
                data.append(self.graph_data[m][name])
                bins = np.arange(0, len(self.int_mapping[m]) + 1, 1)
            n, bins, patches = ax.hist(data, bins=bins, alpha=.25, orientation='horizontal', histtype='barstacked')

        # Draw our plots
        self.plt.subplots_adjust(left=0.2) # Make some room for labels
        self.fig.canvas.draw()
        self.plt.draw()

    def run(self):
        """
            Loop forever consuming output from our SUA threads
        """
        try:
            import matplotlib.pyplot as plt
        except:
            print "ERROR: matplotlib not found. Graphing is disabled."
            sys.exit(0)

        # Interactive mode on
        plt.ion()

        self.fig = plt.figure(figsize=[G.FIG_WIDTH, G.FIG_HEIGHT])
        plt.show()
        self.plt = plt

        # Wait for output to start returning, and handle appropriately
        while True:

            # Get our log data   
            try:
                output = self.DATA_QUEUE.get(True, G.GRAPH_REFRESH_RATE)
#                print output
            except Queue.Empty:
                self.update_graph()
                continue
            except:
                break

            if output == "":
                print "skip data"
                continue

            # If its a kill command, just post it
            if output == G.CTRL_CMD_KILL:
                if G.VERBOSE:
                    print "Grapher killed..."
                break

            # Extract index info
            machine = output['MACHINE']
            name = output['SUA_NAME']
            profile = output['SUA_PROFILE']
            module = output['MODULE_NAME']

            # Is this a module that we care about?
            if module in self.GRAPH_LISTS:

                # Do we have a list for this module yet?
                if module not in self.graph_data:
                    self.graph_data[module] = {}

                # Extract process name column
                tmp = [x[1] for x in output['DATA']]
                # store our numbers, not our names
                tmp = [self.str_to_int(module, x) for x in tmp]
                if machine not in self.graph_data[module] or tmp != self.graph_data[module][machine]:
                    self.graph_data[module][machine] = tmp
                    if G.VERBOSE:
                        print "Grapher: Got data for %s" % machine
                        print self.graph_data[module][machine]
                    self.update_graph()

        # Close our plots
        plt.close("all")

        if G.VERBOSE:
            print "Grapher Closed"
