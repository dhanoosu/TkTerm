import tkinter as tk
import tkinter.messagebox

from tkinter import *
from tkinter import ttk

from tkinter import colorchooser
from tkinter import font
from tkinter.font import Font

import threading
import os
import sys
import subprocess
import time
import json

# Add to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import *

# Configuration filename
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "tkterm_settings.json")

def get_last_line(widget):
    """ Get the position of the last line from Text Widget"""

    pos = widget.index("end linestart")
    pos = float(pos) - 1
    return pos

class Redirect():
    """ Redirect stdout and stderr to be written to Text widget """

    def __init__(self, widget, autoscroll=True, stream="stdout"):
        self.app = widget
        self.TerminalScreen = widget.TerminalScreen
        self.autoscroll = autoscroll
        self.stream = stream
    def write(self, text):

        # Keep line limit for Terminal to 5000 lines
        limit_diff = int(get_last_line(self.TerminalScreen)) - 5000
        for i in range(limit_diff):
            self.TerminalScreen.delete("1.0", "2.0")

        # Work out if the current line is a command or output
        start_pos = get_last_line(self.TerminalScreen)
        line = self.TerminalScreen.get(start_pos, END)
        isCmd = True if line.startswith(self.app.basename) else False

        self.TerminalScreen.insert("end", text)

        if self.autoscroll:
            self.TerminalScreen.see("end")

        ########################################################################
        ## Adding color tags
        ########################################################################

        # Error output
        # would have added a newline, so start_pos needs -1
        if self.stream == "stderr":
            start_pos = get_last_line(self.TerminalScreen) - 1
            end_pos = self.TerminalScreen.index("insert")
            self.TerminalScreen.tag_add("error", start_pos, end_pos)

            # Clear caret handling on invalid commands
            if self.app.caretHandling:
                self.app.set_basename(self.app.oldBasename, postfix="")
                self.app.caretHandling = False

        # Normal output
        else:
            # Basename
            # does not add a newline, so start_pos does not need -1
            if text.startswith(self.app.basename):
                start_pos = get_last_line(self.TerminalScreen)
                end_pos = str(start_pos).split('.')[0] + '.' + str(len(self.app.basename))

                if self.app.caretHandling:
                    self.TerminalScreen.tag_add("command", start_pos, end_pos)
                else:
                    self.TerminalScreen.tag_add("basename", start_pos, end_pos)

            # Normal output - could be command or its output
            # needs start_pos - 1
            elif not isCmd:
                # start_pos = get_last_line(self.TerminalScreen) - 1
                end_pos = self.TerminalScreen.index("insert")
                self.TerminalScreen.tag_add("output", start_pos, end_pos)

        # Gives slightly smoother print out and reduces CPU stress
        # time.sleep(0.0001)


class App(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)

        self.basename = ""
        self.commandIndex = -1
        self.commandHistory = []

        # get the root after
        self.after = self.winfo_toplevel().after

        ########################################################################
        ## Terminal screen
        ########################################################################
        self.frameTerminal = tk.Frame(self, borderwidth=0, relief=FLAT, bg=self.TerminalColors["bg"])

        self.TerminalScreen = tk.Text(
            self.frameTerminal,
            bg=self.TerminalColors["bg"],
            fg=self.TerminalColors["fg"],
            insertbackground="white",
            highlightthickness=0,
            borderwidth=0,
            insertwidth=1,
            undo=False
        )

        self.frameScrollbar = Frame(self.frameTerminal, borderwidth=0, width=14, bg=self.TerminalColors["bg"])
        # tell frame not to let its children control its size
        self.frameScrollbar.pack_propagate(0)

        self.scrollbar = ttk.Scrollbar(self.frameScrollbar, style="Terminal.Vertical.TScrollbar", orient="vertical")
        self.scrollbar.pack(anchor=E, side=RIGHT, fill=Y, expand=True, padx=(0,3))

        self.TerminalScreen['yscrollcommand'] = self.scrollbar.set
        self.scrollbar['command'] = self.TerminalScreen.yview

        self.frameScrollbar.bind("<Enter>", self.on_scrollbar_enter)
        self.frameScrollbar.bind("<Leave>", self.on_scrollbar_leave)

        # Initially map as leave event
        self.frameScrollbar.bind("<Map>", self.on_scrollbar_leave)

        ########################################################################
        ## Status bar
        ########################################################################
        self.frameStatusBar = ttk.Frame(self, style="Status.TFrame")

        self.returnCodeLabel = Label(self.frameStatusBar, text="RC: 0", fg="white", bg="green", font=("Helvetica", 8), anchor=W, width=8)
        self.returnCodeLabel.pack(side=LEFT)

        self.statusText = StringVar()
        self.statusText.set("Status: IDLE")
        self.statusLabel = Label(self.frameStatusBar, textvariable=self.statusText, font=("Helvetica", 8), relief=FLAT)
        self.statusLabel.pack(side=LEFT)


        self.shellMapping = {
            "csh" : "/bin/csh",
            "bash" : "/bin/sh",
            "windows" : None
        }

        ########################################################################
        ## Style configure for ttk widgets
        ########################################################################
        style_combobox = {
            "relief"                : FLAT,
            "borderwidth"           : 0,
            "highlightthickness"    : 0
        }

        self.style = ttk.Style(self)
        self.style.theme_use('default')
        self.style.configure("Shell.TCombobox", **style_combobox)
        self.style.configure("Terminal.Vertical.TScrollbar",
            background="#3A3E48",
            borderwidth=0,
            relief=FLAT
        )

        self.style.configure("Status.TFrame", background="#21252B", borderwidth=0, relief=FLAT)


        # following are style option for the drop down combobox listbox
        self.option_add('*TCombobox*Listbox*Background', '#21252B')
        self.option_add('*TCombobox*Listbox*Foreground', "#9DA5B4")
        self.option_add('*TCombobox*Listbox.font', ("Helvetica", 8))


        self.shellComboBox = ttk.Combobox(self.frameStatusBar, style="Shell.TCombobox", state="readonly", width=8, font=("Helvetica", 8))
        self.shellComboBox.pack(side=RIGHT, padx=0)
        self.shellComboBox['values'] = list(self.shellMapping)

        self.shellComboBox.bind("<<ComboboxSelected>>", self.update_shell)

        ########################################################################
        ## Set style colours
        ########################################################################

        self.set_color_style()

        ########################################################################
        ## Packing
        ########################################################################

        # Need to pack these last otherwise a glitch happens
        # where scrollbar disappear when window resized
        self.frameStatusBar.pack(side=BOTTOM, fill=X)
        self.frameTerminal.pack(side=TOP, fill=BOTH, expand=True)
        self.frameScrollbar.pack(side=RIGHT, fill=Y)
        self.TerminalScreen.pack(side=LEFT, fill=BOTH, expand=True, padx=(4,0), pady=0)


        ########################################################################
        ## Key bindings
        ########################################################################
        self.TerminalScreen.bind('<MouseWheel>', self.rollWheel)
        self.frameScrollbar.bind('<MouseWheel>', self.rollWheel)
        self.scrollbar.bind('<MouseWheel>', self.rollWheel)


        self.TerminalScreen.bind('<Control-c>', self.do_cancel)
        self.bind_keys()

        # Bind all other key press
        self.TerminalScreen.bind("<KeyPress>", self.do_keyPress)

        self.pendingKeys = ""

        self.insertionIndex = self.TerminalScreen.index("end")
        self.count = 0

        self.terminalThread = None

        # Sets default shell based on operating system
        if (os.name == 'nt'):
            self.shellComboBox.set("windows")
        else:
            self.shellComboBox.set("bash")


        self.processTerminated = False

        # Caret handling and multiline commands
        self.multilineCommand = ""
        self.caretHandling = False
        self.oldBasename = self.basename

        # Automatically set focus to Terminal screen when initialised
        self.TerminalScreen.focus_set()

    def reset(self):

        # Caret handling and multiline commands
        self.multilineCommand = ""
        self.caretHandling = False
        self.oldBasename = self.basename

    def set_color_style(self):
        """
        Set coloring style for widgets
        """
        self.TerminalScreen["bg"]               = self.TerminalColors["bg"]
        self.TerminalScreen["fg"]               = self.TerminalColors["fg"]
        self.TerminalScreen["selectbackground"] = self.TerminalColors["selectbackground"]

        self.frameTerminal["bg"] = self.TerminalColors["bg"]
        self.frameScrollbar["bg"] = self.TerminalColors["bg"]

        ########################################################################
        ## Font
        ########################################################################

        terminalFont = Font(family=self.TerminalColors["fontfamily"], size=self.TerminalColors["fontsize"])
        self.TerminalScreen["font"] = terminalFont

        boldFont = Font(font=terminalFont)
        boldFont.configure(weight="bold")

        self.TerminalScreen.tag_config("basename", foreground=self.TerminalColors["basename"], font=boldFont)
        self.TerminalScreen.tag_config("error", foreground=self.TerminalColors["error"])
        self.TerminalScreen.tag_config("output", foreground=self.TerminalColors["output"])

        ########################################################################
        ## Scrollbar
        ########################################################################

        self.style.configure("Terminal.Vertical.TScrollbar", troughcolor=self.TerminalColors["bg"])
        self.style.configure("Terminal.Vertical.TScrollbar", arrowcolor=self.TerminalColors["bg"])

        self.style.map('Terminal.Vertical.TScrollbar',
            background=[
                ('active', "#9DA5B4"), ('pressed', "#9DA5B4"),
                ('disabled', self.TerminalColors["bg"])
            ],
            arrowcolor=[
                ('disabled', self.TerminalColors["bg"]),
                ('active', self.TerminalColors["bg"])
            ]
        )

        ########################################################################
        ## Shell selection combobox
        ########################################################################

        self.style.map('Shell.TCombobox', background=[('hover', "#2F333D")])
        self.style.map('Shell.TCombobox', fieldbackground=[('hover', "#2F333D")])
        self.style.map('Shell.TCombobox', arrowcolor=[('readonly', '#21252B')])

        self.style.configure("Shell.TCombobox", fieldbackground="#21252B") # current field background
        self.style.configure("Shell.TCombobox", background="#21252B") # arrow box background
        self.style.configure("Shell.TCombobox", foreground="#9DA5B4") # current field foreground

        ########################################################################
        ## Status bar
        ########################################################################

        self.statusLabel["bg"] = "#21252B"
        self.statusLabel["fg"] = "#9DA5B4"

        # Use i-beam cursor
        if self.TerminalColors["cursorshape"] == "bar":
            self.TerminalScreen['blockcursor'] = False
            self.TerminalScreen['insertwidth'] = 1

        # Use block cursor
        elif self.TerminalColors["cursorshape"] == "block":
            self.TerminalScreen['blockcursor'] = True
            self.TerminalScreen['insertwidth'] = 0


    def on_scrollbar_enter(self, event):
        """
        On focus on scrollbar increase width of scrollbar
        """

        self.style.configure("Terminal.Vertical.TScrollbar",
            width=10,
            arrowsize=10
        )

    def on_scrollbar_leave(self, eventL):
        """
        On focus off from scrollbar decrease width of scrollbar
        """

        self.style.configure("Terminal.Vertical.TScrollbar",
            width=5,

            # hack to make arrow invisible
            arrowsize=-10
        )

    def bind_keys(self):
        self.TerminalScreen.bind("<Return>",            self.do_keyReturn)
        self.TerminalScreen.bind("<Up>",                self.do_keyUpArrow)
        self.TerminalScreen.bind("<Down>",              self.do_keyDownArrow)
        self.TerminalScreen.bind("<BackSpace>",         self.do_keyBackspace)
        self.TerminalScreen.bind("<Delete>",            lambda event: "")
        self.TerminalScreen.bind("<End>",               lambda event: "")
        self.TerminalScreen.bind("<Left>",              self.do_keyLeftArrow)
        self.TerminalScreen.bind("<Right>",             lambda event: "")
        self.TerminalScreen.bind("<Button-1>",          self.do_leftClick)
        self.TerminalScreen.bind("<ButtonRelease-1>",   self.do_leftClickRelease)
        self.TerminalScreen.bind("<ButtonRelease-2>",   self.do_middleClickRelease)
        self.TerminalScreen.bind("<Tab>",               self.do_keyTab)
        self.TerminalScreen.bind("<Home>",              self.do_keyHome)
        self.TerminalScreen.unbind("<B1-Motion>")

    def unbind_keys(self):
        self.TerminalScreen.bind("<Return>",            lambda event: "break")
        self.TerminalScreen.bind("<Up>",                lambda event: "break")
        self.TerminalScreen.bind("<Down>",              lambda event: "break")
        self.TerminalScreen.bind("<BackSpace>",         lambda event: "break")
        self.TerminalScreen.bind("<Delete>",            lambda event: "break")
        self.TerminalScreen.bind("<End>",               lambda event: "break")
        self.TerminalScreen.bind("<Left>",              lambda event: "break")
        self.TerminalScreen.bind("<Right>",             lambda event: "break")
        self.TerminalScreen.bind("<Button-1>",          lambda event: "break")
        self.TerminalScreen.bind("<ButtonRelease-1>",   lambda event: "break")
        self.TerminalScreen.bind("<ButtonRelease-2>",   lambda event: "break")
        self.TerminalScreen.bind("<Tab>",               lambda event: "break")
        self.TerminalScreen.bind("<Home>",              lambda event: "break")
        self.TerminalScreen.bind("<B1-Motion>",         lambda event: "break")




    def rollWheel(self, event):
        direction = 0
        if event.num == 5 or event.delta == -120:
            direction = 3
        if event.num == 4 or event.delta == 120:
            direction = -3
        self.TerminalScreen.yview_scroll(direction, UNITS)

        return "break"

    def do_keyPress(self, event):

        import string

        # The obvious information
        c = event.keysym
        s = event.state

        # Manual way to get the modifiers
        ctrl  = (s & 0x4) != 0
        alt   = (s & 0x8) != 0 or (s & 0x80) != 0
        shift = (s & 0x1) != 0

        if ctrl:
            return "break"


        char = event.char

        if self.terminalThread:
            self.pendingKeys += char
        elif char in list(string.printable):
            self.pendingKeys = ""
            self.TerminalScreen.insert("insert", char)
            self.TerminalScreen.see(END)

        return "break"

    def update_shell(self, *args):
        self.shellComboBox.selection_clear()
        self.TerminalScreen.focus()

    def do_cancel(self, *args):

        import signal

        # Kill current running process if there is any
        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):

            # Signals TerminalPrint to immediately stops any printout
            self.processTerminated = True
            print("^C")

            if (os.name == 'nt'):
                process = subprocess.Popen(
                    "TASKKILL /F /PID {} /T".format(self.terminalThread.process.pid),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                for line in process.stdout:
                    print(line, end='')
                for line in process.stderr:
                    print(line, file=sys.stderr, end='')

            else:

                os.system("pkill -TERM -P %s" % self.terminalThread.process.pid)

                self.terminalThread.process.kill()
                self.terminalThread.process.terminate()
                # os.kill(self.terminalThread.process.pid, signal.SIGTERM)

                self.terminalThread.process.wait()

        else:

            # Clear multiline commands
            if self.multilineCommand != "":
                self.multilineCommand = ""

            if self.caretHandling:
                # Always clear caret handle
                self.caretHandling = False

                # Reset basename
                self.set_basename(self.oldBasename, postfix="")

            # Clear commands
            self.insert_new_line()
            self.print_basename()

    class TerminalPrint(threading.Thread):

        def __init__(self, outer_instance, cmd):
            threading.Thread.__init__(self)
            # super().__init__(parent, *args, **kwargs)
            self.daemon = True
            self.cmd = cmd
            self.returnCode = 0

            self.process = None

            # Attach outer class instance
            self.outer_instance = outer_instance
            self.shellMapping = outer_instance.shellMapping

        def run(self):

            stdin = subprocess.PIPE

            process_options = {
                "shell"                 : True,
                "stdout"                : subprocess.PIPE,
                "stderr"                : subprocess.PIPE,
                "universal_newlines"    : True,
                "cwd"                   : os.getcwd()
            }

            # Ignore utf-8 decode error which sometimes happens on early terminating
            if os.name != "nt":
                process_options["errors"] = "ignore"

            # Modify shell executable based on selected shell combobox variable
            shellSelected = self.outer_instance.shellComboBox.get()
            process_options['executable'] = self.shellMapping[shellSelected]

            if self.cmd != "":

                with subprocess.Popen(self.cmd, **process_options) as self.process:

                    for line in self.process.stdout:

                        if self.outer_instance.processTerminated:
                            break

                        print(line, end='')

                    for line in self.process.stderr:
                        print(line, file=sys.stderr, end='')


                rc = self.process.poll()
                self.returnCode = rc

            # Always print basename on a newline
            insert_pos = self.outer_instance.TerminalScreen.index("insert")
            if insert_pos.split('.')[1] != '0':
                self.outer_instance.insert_new_line()

            self.outer_instance.print_basename()
            self.outer_instance.processTerminated = False

    def clear_screen(self):
        """ Clear screen and print basename """
        self.TerminalScreen.delete("1.0", END)
        self.print_basename()

    def print_basename(self):
        """ Print basename on Terminal """
        print(self.basename, end='')
        print(self.pendingKeys, end='')
        self.pendingKeys = ""

    def set_basename(self, text, postfix=">>"):

        if text.endswith(" "):
            text = text.rstrip()

        self.basename = text + postfix + " "

    def do_keyHome(self, *args):
        """ Press HOME to return to the start position of command """

        pos = self.get_pos_after_basename()

        self.TerminalScreen.mark_set("insert", pos)
        return "break"

    def get_pos_after_basename(self):
        """ Return starting position of the command """

        pos = get_last_line(self.TerminalScreen)
        pos_integral = str(pos).split('.')[0]
        offset = '.' + str(len(self.basename))
        new_pos = pos_integral + offset

        return new_pos

    def get_cmd(self):
        """ Return command after the basename """

        pos = self.get_pos_after_basename()
        return self.TerminalScreen.get(pos, "end-1c")

    def delete_cmd(self):
        """ Delete command after basename """

        pos = self.get_pos_after_basename()
        self.TerminalScreen.delete(pos, END)

    def do_keyTab(self, *args):
        """ Tab completion """

        # Windows uses backward slash
        # Unix uses forward slash
        slash = os.sep

        raw_cmd = self.get_cmd()
        cmd = raw_cmd

        # Always focus on the last command
        # E.g., "cd folder" : only focus on the last command "folder"
        # Get the last space-separated command
        if cmd == "":
            last_cmd = ""
        elif cmd[-1] == " ":
            last_cmd = ""
        else:
            last_cmd = cmd.split()[-1]

        # Create a pattern to be match with glob
        match_pattern = last_cmd+'*'

        import glob

        cd_children = sorted(glob.glob(match_pattern))
        cd_children = [f+slash if os.path.isdir(f) else f for f in cd_children]

        import re
        import fnmatch

        # glob on Windows are case insensitive - below is a hack to match case-sensitive path
        match = re.compile(fnmatch.translate(match_pattern)).match
        cd_children = [pth for pth in cd_children if match(pth)]

        common_path = os.path.commonprefix(cd_children)

        return_cmd = raw_cmd

        # If common prefix path is not found this is our final command
        # Concatenate with the previous "last command"
        if common_path != "":
            self.delete_cmd()
            return_cmd += common_path[len(last_cmd):]

            print(return_cmd, end='')

        # Also print the files and folders that matched the pattern only if
        # the results have more than one entry
        if len(cd_children) > 1:
            self.insert_new_line()
            print('\n'.join(cd_children))

            self.print_basename()
            print(return_cmd, end='')

        return "break"

    def do_leftClickRelease(self, *args):

        # Unhide cursor
        self.TerminalScreen["insertwidth"] = 1
        self.TerminalScreen["insertbackground"] = "white"

        self.TerminalScreen.mark_set("insert", self.insertionIndex)

    def do_middleClickRelease(self, *args):

        try:
            selected = self.TerminalScreen.selection_get()
        except Exception as e:
            selected = ""

        current_pos = self.TerminalScreen.index(INSERT)
        self.TerminalScreen.insert(current_pos, selected)

        return "break"

    def do_leftClick(self, *args):

        # Hide cursor
        self.TerminalScreen["insertwidth"] = 0
        self.TerminalScreen["insertbackground"] = self.TerminalColors["selectbackground"]

        self.insertionIndex = self.TerminalScreen.index("insert")
        # self.TerminalScreen.mark_set("insert", self.insertionIndex)
        # return "break"
        pass

    def do_keyReturn(self, *args):
        """ On pressing Return, execute the command """

        # Caret character differs on Windows and Unix
        if os.name == "nt":
            CARET = "^"
        else:
            CARET = "\\"

        cmd = self.get_cmd()

        # Empty command - pass
        if cmd == "":
            self.insert_new_line()
            self.print_basename()
            pass

        # Multiline command
        elif cmd.endswith(CARET):

            # Add to command history
            if cmd in self.commandHistory:
                self.commandHistory.pop(self.commandIndex)

            self.commandIndex = -1
            self.commandHistory.insert(0, cmd)

            # Construct multiline command
            self.multilineCommand += cmd.rstrip(CARET)

            # Store old basename only once at the start of caret handling
            if not self.caretHandling:
                self.oldBasename = self.basename
                self.caretHandling = True

            # Update basename and store command as multiline command
            self.set_basename(">", postfix="")

            self.insert_new_line()
            self.print_basename()

        # Valid command
        else:

            # Add to command history
            if cmd in self.commandHistory:
                self.commandHistory.pop(self.commandIndex)

            self.commandIndex = -1
            self.commandHistory.insert(0, cmd)

            # Merge all multiline command and reset basename
            if self.multilineCommand != "":
                cmd = self.multilineCommand + cmd
                self.multilineCommand = ""

                self.set_basename(self.oldBasename, postfix="")
                self.caretHandling = False

            if cmd == "clear" or cmd == "reset":
                self.clear_screen()

            elif "cd" in cmd.split()[0]:
                path = ' '.join(cmd.split()[1:])
                path = os.path.abspath(path)

                if os.path.isdir(path):
                    os.chdir(path)
                    self.set_basename(path)
                    self.insert_new_line()
                    self.set_returnCode(0)
                else:
                    self.insert_new_line()
                    print("cd: no such file or directory: {}".format(path))
                    self.set_returnCode(1)

                self.print_basename()
            else:
                self.insert_new_line()

                self.terminalThread = self.TerminalPrint(self, cmd)
                self.terminalThread.start()

                self.count = 0
                self.unbind_keys()
                self.monitor(self.terminalThread)


        return 'break'

    def do_keyBackspace(self, *args):
        """ Delete a character until the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) >= len(self.basename):
            self.TerminalScreen.delete(index)

        return "break"

    def do_keyLeftArrow(self, *args):
        """ Moves cursor to the left until it reaches the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) < len(self.basename):
            return "break"

    def do_keyUpArrow(self, *args):
        """ Press UP arrow to get previous command in history """

        if self.commandIndex < len(self.commandHistory) - 1:
            self.commandIndex += 1

            self.delete_cmd()

            cmd = self.commandHistory[self.commandIndex]
            print(cmd, end='')

        return 'break'

    def do_keyDownArrow(self, *args):
        """ Press Down arrow to get the next command in history """

        if self.commandIndex >= 1:
            self.commandIndex -= 1

            self.delete_cmd()

            cmd = self.commandHistory[self.commandIndex]
            print(cmd, end='')

        elif self.commandIndex == 0:
            self.commandIndex = -1

            self.delete_cmd()

        return 'break'

    def insert_new_line(self):
        """ Insert a newline in Terminal """
        self.TerminalScreen.insert(END, "\n")
        self.TerminalScreen.mark_set("insert", END)

    def monitor(self, progress_thread):
        """ Monitor running process and update RC and Status on status bar """

        seq1 = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
        seq2 = [".", "..", "...", "....", ".....", "....", "...", ".."]

        if progress_thread.is_alive():

            string = "{} Status: Working {}".format(seq1[self.count], seq2[self.count])
            self.count = (self.count + 1) % 8
            self.statusText.set(string)

            self.after(100, lambda: self.monitor(progress_thread))

        else:
            self.set_returnCode(progress_thread.returnCode)
            self.statusText.set("Status: IDLE")
            self.terminalThread = None

            self.bind_keys()

    def set_returnCode(self, rc):
        """ Set return code on status bar """

        if(rc != 0):
            self.returnCodeLabel.configure(bg="red")
        else:
            self.returnCodeLabel.configure(bg="green")

        self.returnCodeLabel['text'] = "RC: {}".format(rc)

    def run_command(self, cmd):
        """ Print and execute command on terminal """

        while self.terminalThread: pass

        print(cmd, end='')
        self.do_keyReturn()

class RightClickContextMenu:

    def __init__(self, top_level):

        self.top = top_level

        self.showmenu = BooleanVar()
        self.fullscreen = BooleanVar()
        self.readonly = BooleanVar()

        self.bind_menu()

        self.setting_win_top = False

    def bind_menu(self):
        self.menu = tk.Menu(self.top,
            tearoff = 0,
            # bg="#1D1F23",
            bg="white",
            # fg="white",
            borderwidth=0,
            relief="solid",
            activebackground="grey",
            selectcolor="red",
            activeborderwidth=0
        )

        self.menu.add_command(label ="Copy")
        self.menu.add_command(label ="Paste")
        self.menu.add_command(label ="Reload")
        self.menu.add_separator()
        self.menu.add_command(label="Settings...", command=self._showSettings)

        self.top.TerminalScreen.bind("<ButtonRelease-3>", self._popup)
        self.menu.bind('<FocusOut>', self.on_focusout_popup)

    def on_focusout_popup(self, event=None):
        self.menu.unpost()

    def _popup(self, event):

        try:
            # self.menu.tk_popup(event.x_root+1, event.y_root+1)
            self.menu.post(event.x_root+1, event.y_root+1)
            self.menu.focus_set()
        finally:
            self.menu.grab_release()

    def _showSettings(self):

        def _init():

            fieldTexts["background"].set(self.top.TerminalColors["bg"])
            fieldTexts["foreground"].set(self.top.TerminalColors["fg"])
            fieldTexts["basename"].set(self.top.TerminalColors["basename"])
            fieldTexts["error"].set(self.top.TerminalColors["error"])
            fieldTexts["output"].set(self.top.TerminalColors["output"])
            fieldTexts["selectbackground"].set(self.top.TerminalColors["selectbackground"])

            mappings = dict(zip(cursorShapeMappings.values(), cursorShapeMappings.keys()))
            cursorCombobox.set(mappings[self.top.TerminalColors["cursorshape"]])

            fontFamilyCombobox.set(self.top.TerminalColors["fontfamily"])
            fontSizeFieldText.set(self.top.TerminalColors["fontsize"])

        def _do_restoreDefault():

            self.top.TerminalColors = self.top.DefaultTerminalColors.copy()
            _init()

        def _init_sample():

            sampleTerminal["state"] = "normal"

            try:

                isError = False

                sample_font = Font(family=fontFamilyCombobox.get(), size=int(fontSizeFieldText.get()))

                sampleTerminal["bg"] = fieldTexts["background"].get()
                sampleTerminal["selectbackground"] = fieldTexts["selectbackground"].get()
                sampleTerminal["font"] = sample_font

                sampleTerminal.delete("1.0", END)

                boldFont = Font(font=sample_font)
                boldFont.configure(weight="bold")

                sampleTerminal.insert(END, "basename>>")
                sampleTerminal.tag_add("basename", get_last_line(sampleTerminal), sampleTerminal.index("insert"))
                sampleTerminal.tag_config("basename", foreground=fieldTexts["basename"].get(), font=boldFont)

                sampleTerminal.insert(END, " ")

                start_pos = sampleTerminal.index("insert")

                sampleTerminal.insert(END, "command")
                sampleTerminal.tag_add("command", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("command", foreground=fieldTexts["foreground"].get())

                sampleTerminal.insert(END, "\n")

                start_pos = sampleTerminal.index("insert")

                output_text = """\
This is a sample output message from a given command
Second line ...
Third line ...
^C
"""
                sampleTerminal.insert(END, output_text)
                sampleTerminal.tag_add("output", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("output", foreground=fieldTexts["output"].get())


                start_pos = sampleTerminal.index("insert")

                error_text = "Terminate.\nAn error has occurred"
                sampleTerminal.insert(END, error_text)
                sampleTerminal.tag_add("error", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("error", foreground=fieldTexts["error"].get())

            except:
                isError = True

            sampleTerminal["state"] = "disabled"


        def _populate_color_fields(name, row, color="white"):

            label = tk.Label(frameSettings, text=name)

            field = StringVar()
            field.set(color)

            entry = tk.Entry(frameSettings, textvariable=field, relief=FLAT)
            button = tk.Button(frameSettings, width=2, height=1, relief=FLAT, cursor="hand2", command= lambda: _choose_color(field))

            field.trace("w", lambda *args: _update_color(button, field))

            label.grid(sticky="W", padx=(0,10), row=row, column=0)
            entry.grid(sticky="W", row=row, column=1)
            button.grid(sticky="W", padx=10, row=row, column=2)

            fieldTexts[name] = field

        def _update_color(entry, field):
            try:
                entry["text"] = ""
                entry["bg"] = field.get()
                entry["activebackground"] = field.get()
            except:
                entry["text"] = "Err"
                entry["bg"] = "white"
                entry["fg"] = "red"

            _init_sample()

        def _choose_color(field):

            try:
                result = colorchooser.askcolor(title="Color Chooser", parent=self.setting_win_top, initialcolor=field.get())
            except:
                result = colorchooser.askcolor(title="Color Chooser", parent=self.setting_win_top)

            field.set(result[1])

            _init_sample()

        def _do_ok():

            result = _do_apply()

            if result:
                self.setting_win_top.destroy()
            else:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()

        def _do_apply():

            try:
                self.top.TerminalColors["bg"]               = fieldTexts["background"].get()
                self.top.TerminalColors["fg"]               = fieldTexts["foreground"].get()
                self.top.TerminalColors["cursorshape"]      = cursorShapeMappings[cursorCombobox.get()]
                self.top.TerminalColors["fontfamily"]       = fontFamilyCombobox.get()
                self.top.TerminalColors["fontsize"]         = fontSizeFieldText.get()
                self.top.TerminalColors["output"]           = fieldTexts["output"].get()
                self.top.TerminalColors["error"]            = fieldTexts["error"].get()
                self.top.TerminalColors["basename"]         = fieldTexts["basename"].get()
                self.top.TerminalColors["selectbackground"] = fieldTexts["selectbackground"].get()

                self.top.set_color_style()

            except:
                tkinter.messagebox.showerror(title="Invalid input", message="Found invalid input. Please check your settings")
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()
                return False

            return True

        def _update_cursorShapeSelected(*args):
            cursorCombobox.selection_clear()

            _init_sample()

        def _do_saveConfig():

            result = _do_apply()

            if result:
                with open(CONFIG_FILE, "w") as f:
                    f.write(json.dumps(self.top.TerminalColors, indent = 4))

                tkinter.messagebox.showinfo(title="Configuration saved", message="Successfully saved configuration to file.\n{}".format(CONFIG_FILE))

            else:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()

        def _update_FontFamilySelected(*args):

            fontFamilyCombobox.selection_clear()
            _init_sample()

        def _change_font_size(mode):

            assert(mode in ["decrease", "increase"])

            if mode == "decrease":
                fontSizeFieldText.set(int(fontSizeFieldText.get()) - 1)
            elif mode == "increase":
                fontSizeFieldText.set(int(fontSizeFieldText.get()) + 1)

        #
        # If popup window existed, bring it up
        #
        if self.setting_win_top:
            try:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()
                return
            except:
                pass

        #
        # Create new popup window
        #
        self.setting_win_top = Toplevel(self.top.parent)
        self.setting_win_top.geometry("750x500")
        self.setting_win_top.resizable(False, False)

        self.setting_win_top.title("Settings")
        self.setting_win_top.focus_set()

        ########################################################################
        # Notebook
        ########################################################################

        tabControl = ttk.Notebook(self.setting_win_top)

        tab1 = tk.Frame(tabControl)
        tab1.pack(expand=True, fill=BOTH)

        ########################################################################
        # Tabs
        ########################################################################

        tabControl.pack(expand=True, fill=BOTH)
        tabControl.add(tab1, text ='Appearance')

        ########################################################################
        # Frames
        ########################################################################

        frameWrap = tk.Frame(tab1)
        frameWrap.pack(expand=True, fill=BOTH, padx=10, pady=10)

        frameTop = tk.Frame(frameWrap)
        frameTop.pack(expand=True, fill=X)

        frameSettings = tk.Frame(frameTop)
        frameSettings.pack(side=LEFT)

        frameSample = tk.Frame(frameTop, height=300, width=500)
        frameSample.pack_propagate(False)
        frameSample.pack(side=LEFT, padx=(10, 0))

        frameBottom = tk.Frame(tab1, relief=RAISED, bd=1, height=5)
        frameBottom.pack(side=BOTTOM, fill=X, ipadx=10, ipady=10)

        ########################################################################
        # Sample terminal
        ########################################################################

        sampleTerminal = tk.Text(frameSample)
        sampleTerminal.pack(expand=True, fill=BOTH)

        ########################################################################
        #
        ########################################################################

        fieldTexts = {}
        isError = False

        label_terminal = tk.Label(frameSettings, text="Terminal", font="Helvetica 16 bold")
        label_cursor = tk.Label(frameSettings, text="Cursor", font="Helvetica 16 bold")
        label_font = tk.Label(frameSettings, text="Font", font="Helvetica 16 bold")

        label_cusor_shape = tk.Label(frameSettings, text="Cursor shape")

        label_font_size = tk.Label(frameSettings, text="Font size")
        label_font_family = tk.Label(frameSettings, text="Font family")

        cursorShapeMappings = {
            "Bar ( | )" : "bar",
            "Block ( █ )" : "block"
        }


        fontSizeFieldText = IntVar()

        frameFontSize = tk.Frame(frameSettings)
        buttonFontSizeMinus = tk.Button(frameFontSize, text=" - ", relief=GROOVE, command= lambda:_change_font_size(mode="decrease")).pack(side=LEFT)
        entry_font_size = tk.Entry(frameFontSize, textvariable=fontSizeFieldText, relief=FLAT, justify=CENTER, width=5).pack(side=LEFT, ipady=3)
        buttonFontSizePlus = tk.Button(frameFontSize, text=" + ", relief=GROOVE, command= lambda:_change_font_size(mode="increase")).pack(side=LEFT)

        label_terminal.grid(sticky="W", ipady=10, row=2)

        _populate_color_fields(name="background", row=3)
        _populate_color_fields(name="foreground", row=4)
        _populate_color_fields(name="selectbackground", row=5)
        _populate_color_fields(name="basename", row=6)
        _populate_color_fields(name="output", row=7)
        _populate_color_fields(name="error", row=8)

        label_cursor.grid(sticky="W", ipady=10, row=9)
        label_cusor_shape.grid(sticky="W", row=10, column=0)

        cursorCombobox = ttk.Combobox(frameSettings, state="readonly", width=15, font=("Helvetica", 8))
        cursorCombobox['values'] = list(cursorShapeMappings.keys())
        cursorCombobox.bind("<<ComboboxSelected>>", _update_cursorShapeSelected)
        cursorCombobox.grid(sticky="W", ipady=3, row=10, column=1)

        label_font.grid(sticky="W", ipady=10, row=11)
        label_font_size.grid(sticky="W", row=12, column=0)
        frameFontSize.grid(sticky="W", row=12, column=1)

        label_font_family.grid(sticky="W", row=13, column=0)

        fontFamilyCombobox = ttk.Combobox(frameSettings, state="readonly", width=25)
        fontFamilyCombobox["values"] = list(font.families())
        fontFamilyCombobox.bind("<<ComboboxSelected>>", _update_FontFamilySelected)
        fontFamilyCombobox.grid(sticky="W", ipady=3, row=13, column=1)

        ttk.Button(frameBottom, style="Settings.TButton", text="Restore default", command=_do_restoreDefault).pack(side=LEFT, expand=True)

        ttk.Button(frameBottom, style="Settings.TButton", text="OK", command=_do_ok).pack(side=LEFT)
        ttk.Button(frameBottom, style="Settings.TButton", text="Apply", command=_do_apply).pack(side=LEFT)

        ttk.Button(frameBottom, style="Settings.TButton", text="Save config", command=_do_saveConfig).pack(side=LEFT, expand=True)

        s = ttk.Style()
        s.map('Settings.TButton',
            background=[('disabled','#d9d9d9'), ('active','#ececec')],
            foreground=[('disabled','#a3a3a3')])


        fontSizeFieldText.trace("w", lambda *args: _init_sample())


        _init()
        _init_sample()

class Terminal(SearchFunctionality, App):

    """ Terminal widget """

    def __init__(self, parent, *args, **kwargs):

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        # Default terminal settings
        self.DefaultTerminalColors = {
            "fg"                : "#00A79D",
            "bg"                : "#282C34",
            "insertbackground"  : "white",
            "error"             : "red",
            "output"            : "#E6E6E6",
            "basename"          : "#0080ff",
            "cursorshape"       : "bar",
            "selectbackground"  : "#464E5E",
            "fontfamily"        : "Cascadia Code SemiLight",
            "fontsize"          : 9
        }

        if "Cascadia Code SemiLight" in font.families():
            self.DefaultTerminalColors["fontfamily"] = "Cascadia Code SemiLight"
        else:
            self.DefaultTerminalColors["fontfamily"] = "Consolas"

        self.TerminalColors = self.DefaultTerminalColors.copy()

        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

                for k in data.keys():
                    if k in self.TerminalColors.keys():
                        self.TerminalColors[k] = data[k]


        # Initialise super classes
        super().__init__(parent, *args, **kwargs)

        self.parent = parent
        self.parent.bind("<Configure>", self.on_resize)

        sys.stdout = Redirect(self, stream="stdout")
        sys.stderr = Redirect(self, stream="stderr")

        self.set_basename(os.getcwd())
        self.print_basename()

        self.Search_init()
        self.contextMenu = RightClickContextMenu(self)




    def on_resize(self, event):
        """Auto scroll to bottom when resize event happens"""

        first_visible_line = self.TerminalScreen.index("@0,0")

        if self.scrollbar.get()[1] >= 1:
            self.TerminalScreen.see(END)
        # elif float(first_visible_line) >  1.0:
        #     self.TerminalScreen.see(float(first_visible_line)-1)

        # self.statusText.set(self.TerminalScreen.winfo_height())


if __name__ == "__main__":

    root = tk.Tk()
    root.title("TkTerm - Terminal Emulator")
    root.geometry("700x400")


    terminal = Terminal(root, bg="#282C34", bd=0)
    terminal.pack(expand=True, fill=BOTH)

    # root.iconbitmap(default='icon.png')

    photo = PhotoImage(file="icon.png")
    root.iconphoto(False, photo)

    root.mainloop()