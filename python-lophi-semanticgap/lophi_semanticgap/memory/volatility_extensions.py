# Native
import cStringIO
import logging
logger = logging.getLogger(__name__)


# import volatility.plugins.gui.messagehooks as messagehooks

LOPHI_TIMEOUT = 100
LOPHI_RETRIES = 5

pil_installed = True
try:
    from PIL import Image, ImageDraw
except ImportError:
    pil_installed = False

class VolatilityWrapper:
    
    
    def __init__(self, uri, profile, memory_size):
        """    
            Initialize volatility with all of our parameters
            
            @param uri: URI to read from (e.g. lophi://, file://, vmi://)
            @param profile: Volatility profile (e.g. WinXPSP3x86)
            @param memory_size: Memory size in bytes 
        """
        
        logger.debug("Initializg volatility: uri: %s, profile: %s, mem: %s"%(
                                                                             uri,
                                                                             profile,
                                                                             memory_size))
        
        self.MODULE_MAP = {"pslist":self._render_pslist,
                           "ssdt":self._render_ssdt,
                           "windows":self._render_windows,
                           "screenshot":self._render_screenshot}
        
        self.uri = uri
        self.profile = profile
        self.memory_size = memory_size
        
        # Import all of our Volatility classes
        
        import volatility.registry as MemoryRegistry # @UnresolvedImport
        import volatility.utils as utils # @UnresolvedImport
        import volatility.cache as cache # @UnresolvedImport
        import volatility.debug as debug # @UnresolvedImport
        import volatility.addrspace as addrspace # @UnresolvedImport
        import volatility.commands as commands # @UnresolvedImport
        self.MemoryRegistry = MemoryRegistry
        self.utils = utils
        self.commands = commands
        self.addrspace = addrspace
        
        # Hack to disable caching
#         cache.disable_caching(0, 0, 0, 0)

        # Initialize Volatility
        self.volatility_config = None
        self.init_ok = self._init_volatility_config()
        
        # Did everything init ok?
        if self.init_ok == False:
            #logger.error("Could not start memory analysis for %s."%self.machine.name)
            logger.error("Could not start memory analysis for uri %s."%self.uri)
            return
        
        # Import our plugins module
        self.PLUGIN_COMMANDS = None
        try:
            logger.debug("Init MemoryRegistry")
            # try the older method which had an init function
            self.MemoryRegistry.Init()
            self.PLUGIN_COMMANDS = self.MemoryRegistry.PLUGIN_COMMANDS
        except:
            logger.debug("Plugin Importer MemoryRegistry (version 2.2+)")
            self.MemoryRegistry.PluginImporter()
            self.MemoryRegistry.register_global_options(self.volatility_config, self.addrspace.BaseAddressSpace)
            self.MemoryRegistry.register_global_options(self.volatility_config, self.commands.Command)
            self.PLUGIN_COMMANDS = self.MemoryRegistry.get_plugin_classes(self.commands.Command, lower=True)

        self.command_objs = {}
        self.addr_space = None


    def _init_volatility_config(self):
        """
            Creates a new Volatility ConfObject with its own storage
        """

        import volatility.conf as conf # @UnresolvedImport
        
        if not self.volatility_config:
            config = conf.ConfObject()
            # Set all of our static settings
            config.update('DONOTLOADADDRSPACE', True)
            config.update('LOCATION', self.uri)
            config.update('DTB', None)
            config.update('KDBG', None)
            config.update('NO_CACHE', True)             # IMPORTANT: No Cache!
#             config.update("OUTPUT", OUTPUT_TYPE)
            config.update("CACHE_DTB", False)

            # LOPHI Addrspace stuff
            config.update("RAM_SIZE", self.memory_size)
#             config.update('RETRIES', LOPHI_RETRIES)
#             config.update('TIMEOUT', LOPHI_TIMEOUT)
            
            # Ensure our profile is valid and assign it
            if self._is_valid_profile(self.profile):
                config.update('PROFILE', self.profile)
            else:
                logger.error("Unrecognized Profile (%s)." % self.profile)
                return False

            self.volatility_config = config
            self.config = property(self.volatility_config)
        return True


    def _is_valid_profile(self, profile_name):
        """
            Just a nice simple function to check if a profile is valid
        """
        return True
        for p in self.MemoryRegistry.PROFILES.classes:
            if p.__name__ == profile_name:
                return True
        return False
    
    def execute_plugin(self,plugin_name):
        
        """
            This will execute a volatility plugin, render its output with one of
             our render functions, and return that output
             
             @param plugin_name: Name of plugin as you would use on the command line 
        """
        logger.debug("Executing volatility plugin: %s"%plugin_name)
        
        if plugin_name not in self.PLUGIN_COMMANDS:
            logger.error("%s is not a valid plugin for this Volatility installation")
            return False
        
        # Initialize every module  (No need to recall it everytime)
        if plugin_name not in self.command_objs:
            command = self.PLUGIN_COMMANDS[plugin_name]
            command_obj = command(self.volatility_config)
            self.command_objs[plugin_name] = command_obj
            
        # Initialize our address space (Only do this once)
        if self.addr_space is None:
            self.addr_space = self.utils.load_as(self.volatility_config)

        # Enable our cache
        self.volatility_config.update('LOPHI_CACHE',True)
                    
        # Get our results for this module
        command_obj = self.command_objs[plugin_name]
#       data = command_obj.calculate()
        data = command_obj.calculate(self.addr_space)

        # Disable and wipe our cache
        self.volatility_config.update('LOPHI_CACHE',False)
                    
        # Render out output into the format we want
        output = self._render_data(plugin_name, self.addr_space, data)
    
        if output is not None:
            # We have to append our output specific info for processing
            output['MODULE'] = plugin_name
            output['URI'] = self.uri
            output['PROFILE'] = self.profile
        else:
            stringio = cStringIO.StringIO()
            command_obj.render_text(stringio, data)
            output = stringio.getvalue()
            stringio.close()

        return output
    
    
    def _render_data(self,module_name, addr_space, data):
        """
            Given volatility plugin output, will attempt to render it into a 
            format that we have specified
        """
        logger.debug("Trying to process data for %s"%module_name)
        if module_name in self.MODULE_MAP:
            return self.MODULE_MAP[module_name](addr_space,data)
        else:
            return None
    
    
    def _render_screenshot(self, addr_space, data):
        """
            Render the screenshot data and return a Python Image object
            
            To save the output as images:
            
                data[0].save(header[0]+".png","PNG")
                
            Note: This plug seg faults, which is why we are only returning the
            default screen
        """
        def draw_text(draw, text, left, top, fill = "Black"):
            """Label windows in the screen shot"""
            lines = text.split('\x0d\x0a') 
            for line in lines:
                draw.text( (left, top), line, fill = fill)
                _, height = draw.textsize(line)
                top += height

        if not pil_installed:
            logger.error("Must install PIL for this plugin.")
            return None
        
        out_header = []
        out_data = []
        
        seen = []

        found = False
        for window_station in data:
            if found:
                break
            
            for desktop in window_station.desktops():
                
                session_name = "session_{0}.{1}.{2}".format(
                                            desktop.dwSessionId,
                                            window_station.Name, desktop.Name)

                
                offset = desktop.PhysicalAddress
                if offset in seen:
                    continue
                seen.append(offset)

                # The foreground window 
                win = desktop.DeskInfo.spwnd
                
                # Some desktops don't have any windows
                if not win:
                    logger.info("{0}\{1}\{2} has no windows (Skipping)".format(
                        desktop.dwSessionId, window_station.Name, desktop.Name))
                    continue
                
                im = Image.new("RGB", (win.rcWindow.right + 1, win.rcWindow.bottom + 1), "White")
                draw = ImageDraw.Draw(im)
 
                # Traverse windows, visible only
                for win, _level in desktop.windows(
                                        win = win,
                                        filter = lambda x : 'WS_VISIBLE' in str(x.style)):
                    draw.rectangle(win.rcWindow.get_tup(), outline = "Black", fill = "White")
                    draw.rectangle(win.rcClient.get_tup(), outline = "Black", fill = "White")
                      
                    ## Create labels for the windows 
                    draw_text(draw, str(win.strName or ''), win.rcWindow.left + 2, win.rcWindow.top)
                        
                del draw

                out_header.append(session_name)
                out_data.append(im)
                break

        # Return our output
        if len(out_data) > 0:
            return {'HEADER':out_header,'DATA':out_data}
        else:
            return {'HEADER':[],'DATA':[]}
    
    
    # Render Abstract method added by Chad Spensky for LO-PHI
    def _render_pslist(self, addr_space, data):
        offsettype = "(V)"
        out_header = ['Offset'+offsettype,'Name', 'Pid', 'PPid', 'Thds', 'Hnds', 'Time']
        out_data = []
        for task in data:
            offset = task.obj_offset
            try:
                out_data.append(map(str,[
                    hex(offset),
                    task.ImageFileName,
                    task.UniqueProcessId,
                    task.InheritedFromUniqueProcessId,
                    task.ActiveThreads,
                    task.ObjectTable.HandleCount,
                    task.CreateTime]))
            except:
                logger.error("Could not convert column to string")
        
        return {'HEADER':out_header,'DATA':out_data}
    

    def _render_windows(self,addr_space,data):
        """
            Render the windows module output into a nice dict
        """
        
        def translate_atom(winsta, atom_tables, atom_id):
            """
            Translate an atom into an atom name.
    
            @param winsta: a tagWINDOWSTATION in the proper 
            session space 
    
            @param atom_tables: a dictionary with _RTL_ATOM_TABLE
            instances as the keys and owning window stations as
            the values. 
    
            @param index: the index into the atom handle table. 
            """
            import volatility.plugins.gui.constants as consts
            # First check the default atoms
            if consts.DEFAULT_ATOMS.has_key(atom_id):
                return consts.DEFAULT_ATOMS[atom_id].Name
    
            # A list of tables to search. The session atom tables
            # have priority and will be searched first. 
            table_list = [
                    table for (table, window_station)
                    in atom_tables.items() if window_station == None
                    ]
            table_list.append(winsta.AtomTable)
    
            ## Fixme: the session atom tables are found via physical
            ## AS pool tag scanning, and there's no good way (afaik)
            ## to associate the table with its session. Thus if more
            ## than one session has atoms with the same id but different
            ## values, then we could possibly select the wrong one. 
            for table in table_list:
                atom = table.find_atom(atom_id)
                if atom:
                    return atom.Name
    
            return None
        
        
        output_dict = {}
        for winsta, atom_tables in data:
            for desktop in winsta.desktops():
                # Create our hierarchy 
                if winsta.dwSessionId not in output_dict:
                    output_dict[winsta.dwSessionId] = {}
                if winsta.Name not in output_dict[winsta.dwSessionId]:
                    output_dict[winsta.dwSessionId][winsta.Name] = {}
                if desktop.Name not in output_dict[winsta.dwSessionId][winsta.Name]:
                    output_dict[winsta.dwSessionId][winsta.Name][desktop.Name] = []
                    
                output_dict[winsta.dwSessionId][winsta.Name][desktop.Name]
                
                for wnd, _level in desktop.windows(desktop.DeskInfo.spwnd):
                    
                    window_dict = {'windowhandle':wnd.head.h,
                                   'windowhandle_addr':wnd.obj_offset,
                                   'name':str(wnd.strName or ''),
                                   'classatom':wnd.ClassAtom,
                                   'class':translate_atom(winsta, atom_tables, wnd.ClassAtom),
                                   'superclassatom':wnd.SuperClassAtom,
                                   'superclass':translate_atom(winsta, atom_tables, wnd.SuperClassAtom),
                                   'pti':wnd.head.pti.v(),
                                   'tid':wnd.Thread.Cid.UniqueThread,
                                   'tid_addr':wnd.Thread.obj_offset,
                                   'ppi':wnd.head.pti.ppi.v(),
                                   'process':wnd.Process.ImageFileName,
                                   'pid':wnd.Process.UniqueProcessId,
                                   'visible':wnd.Visible,
                                   'left':wnd.rcClient.left,
                                   'top':wnd.rcClient.top,
                                   'bottom':wnd.rcClient.bottom,
                                   'right':wnd.rcClient.right,
                                   'style_flags':wnd.style,
                                   'exstyle_flags':wnd.ExStyle,
                                   'windows_proc':wnd.lpfnWndProc
                    }
                    
                    
                    # Append this window to our list
                    output_dict[winsta.dwSessionId][winsta.Name][desktop.Name].append(window_dict)
        
        # Return our out nested dictionaries
        return {'DATA':output_dict}


    def _render_ssdt(self,addr_space,data):
        
        from bisect import bisect_right
        # Volatility
        import volatility.obj as obj
        
        def find_module(modlist, mod_addrs, addr):
            """Uses binary search to find what module a given address resides in.
        
            This is much faster than a series of linear checks if you have
            to do it many times. Note that modlist and mod_addrs must be sorted
            in order of the module base address."""
        
            pos = bisect_right(mod_addrs, addr) - 1
            if pos == -1:
                return None
            mod = modlist[mod_addrs[pos]]
        
            if (addr >= mod.DllBase.v() and
                addr < mod.DllBase.v() + mod.SizeOfImage.v()):
                return mod
            else:
                return None
        syscalls = addr_space.profile.syscalls

        # Print out the entries for each table
        out_header = ['SSDT Index','Table','Entry Count','Entry Index','Address', 'Name', 'Owner Module']
        out_data = []
        for idx, table, n, vm, mods, mod_addrs in data:
            
            
            if vm.is_valid_address(table):
                for i in range(n):
                    syscall_addr = obj.Object('unsigned long', table + (i * 4), vm).v()
                    try:
                        syscall_name = syscalls[idx][i]
                    except IndexError:
                        syscall_name = "Unknown"

                    syscall_mod = find_module(mods, mod_addrs, syscall_addr)
                    if syscall_mod:
                        syscall_modname = syscall_mod.BaseDllName
                    else:
                        syscall_modname = "UNKNOWN"
                    out_data.append(map(str,[
                        idx, 
                        table, 
                        n,
                        "%06x"%(idx * 0x1000 + i),
                        "%x"%syscall_addr,
                        syscall_name,
                        "{0}".format(syscall_modname)
#                         "WTF"
                        ]))
            else:
                    out_data.append(map(str[
                        idx, 
                        table, 
                        n,
                        0,
                        0,
                        0,
                        0]))
                    
        return {'HEADER':out_header,'DATA':out_data}
#                 outfd.write("  [SSDT not resident at 0x{0:08X} ]\n".format(table))





class ButtonClicker():
    """
        This module wraps volatility to click buttons using memory introspection.
    """
    # Names of buttons that we don't want to click.
    bad_button_names = ['save',
                        'reject',
                        'print',
                        'decline',
                        'back',
                        'cancel',
                        'exit',
                        'close']
    
    def __init__(self, uri, profile, mem_size, control_sensor):
        """
            Initialize our volatility instance fro our machine object.
        """
        
        self._vol = VolatilityWrapper(uri,profile,mem_size)
        
        # Init our previous butonns list
        self.buttons_prev = {}
        # Store our machine
        self.control_sensor = control_sensor
        
    
    def _is_bad_button(self, name):
        """
            Check a button name and see if it is in our list of buttons we 
            shouldn't click
            
            @param name: String to compare against our list 
        """
        for b in self.bad_button_names:
            if b.lower() in str(name).lower():
                return True
            
        return False
    
    
    def __get_windows(self):
        """
            Use our volatility instance to get the list of windows on the machine.
        """
        
        return self._vol.execute_plugin("windows")
    
    
    def _get_buttons(self):
        
        
        # Get our list of windows
        windows = self.__get_windows()
        
        # Create list to store buttons
        buttons = []
        
        # Loop through all windows extracting buttons
        for session in windows['DATA']:
            session_dict = windows['DATA'][session]
            for window_ctx in session_dict:
                window_dict = session_dict[window_ctx]
                for desktop in window_dict:
                    desktop_dict = window_dict[desktop]
                    
                    for window in desktop_dict:
                        
                        # Ensure it is a Windows button Atom
                        if window['superclassatom'] == 0xc017 \
                            or window['classatom'] == 0xc061 \
                            or window['class'] == "Button" \
                            or window['superclass'] == "Button":
                            
                            buttons.append({"name":str(window['name']),
                                            "process":str(window['process']),
                                            "visible":str(window['visible']),
                                            "top":int(window['top']),
                                            "left":int(window['left'])
                                            })
        return buttons
        
    
    def update_buttons(self):
        """
            Simply extract the list of current buttons and save them
            
            Meant to be used by calling this, then eventually click_buttons with
            new_only = True.
        """
        self.buttons_prev = self._get_buttons()
    
    
    def click_buttons(self, process=None, new_only=False):
        """
            Attempt to click all buttons
            
            @param process: If provided will only click buttons assigned to 
            this proccess name
            @param new_only: If true, will only click buttons new since the 
            last funciton call 
        """
        
        buttons = self._get_buttons()
        
        clicked = []
        
        for button in buttons:
            
            # Extract our location to click
            (top, left) = (button['top'], button['left'])
            
            btn_o = "[ Button ]" 
            btn_o += "  Name: %s"%button['name']
            btn_o += "  Process: %s"%button['process']
            btn_o += "  Visible: %s"%button['visible']
            btn_o += "  (Top,Left): (%d, %d)"%(top,left)
            
            logger.info(btn_o)
            
            # Are we filtering a specific process?
            if process is not None and process != str(button['process']):
                logger.info("Button not in process specified, skipping.")
                continue
            
            # Are we only clicking new windows
            if new_only and button in self.buttons_prev:
                # Hack: Just catch the key error if the keys don't exist.    
                logger.info("Button not new, skipping.")
                continue


            # Does it match a bad word?
            if self._is_bad_button(button['name']):
                logger.info("Button has a bad word, skipping.")
                continue
            
            # Click it!                            
            self.control_sensor.mouse_click(left,top)
            
            clicked.append(button)
                            
        # Save these windows for later
        self.buttons_prev = buttons
        
        return clicked
