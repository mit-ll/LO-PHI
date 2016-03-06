"""
    This file contains everything needed to launch a GUI to output LO-PHI data.
    The GUI takes a configs and queue as the input and spawns off a worker 
    thread that will handle passing all of the data in.  Most of the classes
    are just wxPython stuff.  LoPhiGUI is the only one needed to interact with
    the outside world.
    
    (c) 2015 Massachusetts Institute of Technology
"""

# Native
import threading
import time

# 3rd Party
import wx

# LO-PHI
import lophi.globals as G

# Unique result IDs for GUI events
EVENT_RESULT_ID = wx.NewId()
NEW_FRAME_ID = wx.NewId()
CLOSE_FRAME_ID = wx.NewId()

# Keep a list of modules that are lists and not updated values
LIST_MODULES = ["disk_engine","alert:critical","alert"]

#
#    START EVENTS
#
def EVENT_RESULT(win, func):
    """
        Connect our event listener so that our worker thread can return output.
    """
    win.Connect(-1, -1, EVENT_RESULT_ID, func)

class ResultEvent(wx.PyEvent):
    """
        Simple result event to pass back to GUI
    """
    def __init__(self, data):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVENT_RESULT_ID)
        self.data = data


def EVENT_NEW_FRAME(win, func):
    """
        Connect our event listener so we can add new frames after the app 
        is running
    """
    win.Connect(-1, -1, NEW_FRAME_ID, func)

class NewFrameEvent(wx.PyEvent):
    """
        Simple result event to open a new frame
    """
    def __init__(self, output_queue, machine_name):
        wx.PyEvent.__init__(self)
        self.SetEventType(NEW_FRAME_ID)
#        self.lophi_config = lophi_config
        self.machine_name = machine_name
        self.output_queue = output_queue


def EVENT_CLOSE_FRAME(win, func):
    """
        Connect our event listener so we can add new frames after the app 
        is running
    """
    win.Connect(-1, -1, CLOSE_FRAME_ID, func)

class CloseFrameEvent(wx.PyEvent):
    """
        Simple result event to open a new frame
    """
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(CLOSE_FRAME_ID)
#        self.lophi_config = lophi_config
#        self.machine_config = machine_config
#
#    END EVENTS
#

class GUIThread(threading.Thread):
    """
        This thread just runs in the background and relays the queue to the
        GUI via wx.PyEvents
    """
    def __init__(self, data_queue, lophi_gui):
        threading.Thread.__init__(self)
        self.LOPHI_GUI = lophi_gui
        self.DATA_QUEUE = data_queue

    def run(self):
        # Wait for output to start returning, and handle appropriately
        while True:

            # get our data to display
            output = self.DATA_QUEUE.get()

            # Are we getting killed?
            if output == G.CTRL_CMD_KILL:
                if G.VERBOSE:
                    print "GUI Relay killed..."
                break

            if self.LOPHI_GUI is not None:
                # Post the event to our GUI
                wx.PostEvent(self.LOPHI_GUI, ResultEvent(output))


class TabPanel(wx.Panel):
    """ Just a simple tab panel """
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListCtrl(self,
                                wx.ID_ANY,
                                style=wx.LC_REPORT | wx.SUNKEN_BORDER,
                                size=(G.GUI_WIDTH - 10, G.GUI_HEIGHT - 70))
        self.SetSizer(sizer)


class NotebookGUI(wx.Notebook):
    """
        This class just handles the tabs in the GUI
    """
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, id=wx.ID_ANY, style=wx.BK_DEFAULT)
        self.lists = {}

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)

    def get_list(self, plugin):
        """
            Return the list used to display results for a particular plugin.
            Creates it if it does not exist
            
            @param plugin: Name of plugin to get list object for
            @return: List object
        """
        if plugin not in self.lists:
            tab = TabPanel(self)
            tab.SetBackgroundColour("Gray")
            self.AddPage(tab, plugin)
            self.lists[plugin] = tab.list

        return self.lists[plugin]
    def OnPageChanged(self, event):
        event.Skip()

    def OnPageChanging(self, event):
        event.Skip()

class LoPhiFrame(wx.Frame):
    """
        This is the tab frame that will reflect the configuration for the SUA
    """
    def __init__(self, parent, gui_id, name):
#        self.sua_config = lophi_config
        # create our frame
        wx.Frame.__init__(self,
                          parent,
                          gui_id,
                          "LO-PHI: " + name,
                          pos=(25, 25),
                          size=(G.GUI_WIDTH, G.GUI_HEIGHT),
                        style=wx.DEFAULT_FRAME_STYLE,
                        name="LO-PHI GUI")
        self.statusbar = self.CreateStatusBar()
        panel = wx.Panel(self)
        # Create our tab setup, the modules in LoPhiConfig object will specify 
        #  the tab names
        self.notebook = NotebookGUI(panel)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)
        panel.SetSizer(sizer)
        self.Layout()
        # Not sure what these do...
        ns = {}
        ns['wx'] = wx
        ns['app'] = self
        ns['frame'] = self
        # Show the frame and bind the close event
        self.Show(True)
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)


    def OnExitApp(self, event):
        self.frame.Close(True)

    def OnCloseFrame(self, evt):
        evt.Skip()



class LoPhiGUI(wx.App, threading.Thread):
    """
        This class launches the GUI for LO-PHI.  
        Each SUA is a frame in this class.  
        The ways to update them are all handled by dictionaries of lists and 
        wxEvents
    """
    def __init__(self):
        """ Init the wx App """

        # Init our thread
        threading.Thread.__init__(self)

        # Keep track to see if a module's headers were initialized    
        self.initLists = {}
        self.frames = {}
        self.queues = {}

        # Init the App
        wx.App.__init__(self, redirect=False)


    def OnInit(self):
        # Subscribe to our event
        EVENT_RESULT(self, self.report_output)
        EVENT_NEW_FRAME(self, self.new_frame_event)
        EVENT_CLOSE_FRAME(self, self.close_frame_event)
        return True


    def close_frame_event(self, event):
        """ Catch our close frame event and close the frame """

        # Get all of our important information 
        results = event.data

        # Extract Data
        machine_name = results['MACHINE']

        # Close frame
        self.frames[machine_name].Close(True)

        # Clean up pointers
        del self.frames[machine_name]
        del self.initLists[machine_name]


    def new_frame_event(self, event):
        """ Catch our new frame event """

        # Extract data
        output_queue = event.output_queue
        machine_name = event.machine_name

        # create new frame
        self.new_frame(output_queue, machine_name)


    def new_frame(self, output_queue, machine_name):
        """ Creates a new frame and starts a data relay thread """

        # Create our frame
        self.frames[machine_name] = LoPhiFrame(None, -1, machine_name)
        self.queues[machine_name] = output_queue

        # Setup our lists to keep track of which modules were initialized
        self.initLists[machine_name] = []

        # Setup our thread to relay data to us
        new_thread = GUIThread(output_queue, self)
        new_thread.start()

    def report_output(self, event):
        """ 
            The controller program will call this function with the output from 
            a given SUA and module, both of which are specified in the 
            event.data
        """

        # Get all of our important information 
        results = event.data

        # Extract Data
        plugin_name = results['MODULE']
        machine_name = results['MACHINE']

        if machine_name not in self.frames:
            print "ERROR: Got data for a machine that was never initialized. (%s)" % machine_name
            return

        try:
            self.frames[machine_name].GetStatusBar()
        except wx.PyDeadObjectError:
            self.new_frame(self.queues[machine_name], machine_name)

        # Get our context
        initList = self.initLists[machine_name]
        frame = self.frames[machine_name]



        # Init our index vars
        idx = 0
        row = 0

        # Update our status bar
        frame.SetStatusText("Updated: %s" % (time.asctime()), 0)

        # Get the list that we are updating (If it's dead, we just ignore it)
        plugin_list = frame.notebook.get_list(plugin_name)


        # Only update the column headers once.  They don't change.
        if plugin_name not in initList:
            for col_title in results['HEADER']:
                plugin_list.InsertColumn(idx, col_title, wx.LIST_AUTOSIZE)
                idx += 1

        # Keep our state  
        scrollX = plugin_list.GetScrollPos(wx.HORIZONTAL)
        scrollY = plugin_list.GetScrollPos(wx.VERTICAL)
        selected = plugin_list.GetFirstSelected(wx.LIST_NEXT_ALL)

        # Should we clear old data?
        if plugin_name not in LIST_MODULES:
            plugin_list.DeleteAllItems()

        # Update the data in the list    
        for data_row in results['DATA']:
            # If its a log, we always append
            if plugin_name in LIST_MODULES:
                row = plugin_list.InsertStringItem(plugin_list.GetItemCount(), str(data_row[0]))
            else:
                row = plugin_list.InsertStringItem(0, str(data_row[0]))

            # Fill in the columns
            col = 1
            for data in data_row[1:]:
                plugin_list.SetStringItem(row, col, str(data))
                col += 1
            row += 1

        # Refresh our list
        plugin_list.Refresh()

        # Update our scroll and selection
        if plugin_name in LIST_MODULES:
            plugin_list.EnsureVisible(plugin_list.GetItemCount() - 1)
        else:
            plugin_list.SetScrollPos(wx.HORIZONTAL, scrollX)
            plugin_list.SetScrollPos(wx.VERTICAL, scrollY, refresh=True)

        if selected >= 0:
            plugin_list.Select(selected, on=1)

        # Note that the list was initialized
        if plugin_name not in initList:
            initList.append(plugin_name)


    def run(self):
        """ Run this as a thread """

        # hidden frame has to be here so the app will remain running... H4X!
        top = wx.Frame(None, title="LOPHI HIDDEN FRAME", size=(300, 200))

        # Start main loop
        if G.VERBOSE:
            print "GUI: Running MainLoop..."
        self.MainLoop()
        
        
class AlertGUI(LoPhiGUI):
    
    def report_output(self, event):
        """ 
            The controller program will call this function with the output from 
            a given SUA and module, both of which are specified in the 
            event.data
        """

        # Get all of our important information 
        results = event.data

#         print "got %s"%results

        # Extract Data
        plugin_name = results['MODULE']
        machine_name = results['MACHINE']
        
        # Support colors
        bg_color = "#FFFFFFF"
        text_color = "#000000"
        if "COLOR" in results:
            bg_color = results['COLOR'][0]
            text_color = results['COLOR'][1]

        if machine_name not in self.frames:
            print "ERROR: Got data for a machine that was never initialized. (%s)" % machine_name
            return

        try:
            self.frames[machine_name].GetStatusBar()
        except wx.PyDeadObjectError:
            self.new_frame(self.queues[machine_name], machine_name)

        # Get our context
        initList = self.initLists[machine_name]
        frame = self.frames[machine_name]



        # Init our index vars
        idx = 0
        row = 0

        # Update our status bar
        frame.SetStatusText("Updated: %s" % (time.asctime()), 0)

        # Get the list that we are updating (If it's dead, we just ignore it)
        plugin_list = frame.notebook.get_list(plugin_name)


        # Only update the column headers once.  They don't change.
        if plugin_name not in initList:
            for col_title in results['HEADER']:
                plugin_list.InsertColumn(idx, col_title, wx.LIST_AUTOSIZE)
                idx += 1

        # Keep our state  
        selected = plugin_list.GetFirstSelected(wx.LIST_NEXT_ALL)

        # Update the data in the list    
        for data_row in results['DATA']:
            row = plugin_list.InsertStringItem(plugin_list.GetItemCount(), str(data_row[0]))
            
            plugin_list.SetItemBackgroundColour(item=row,col=bg_color)
            plugin_list.SetItemTextColour(item=row,col=text_color)
            
            # Fill in the columns
            col = 1
            for data in data_row[1:]:
                plugin_list.SetStringItem(row, col, str(data))
                
                col += 1
            row += 1

        # Refresh our list
        plugin_list.Refresh()

        # Update our scroll and selection
        plugin_list.EnsureVisible(plugin_list.GetItemCount() - 1)

        if selected >= 0:
            plugin_list.Select(selected, on=1)

        # Note that the list was initialized
        if plugin_name not in initList:
            initList.append(plugin_name)
