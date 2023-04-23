import tkinter as tk
import tkinter.messagebox

from tkinter import *
from tkinter import ttk

from tkinter import font
from tkinter.font import Font

import threading
import os
import sys
import subprocess

from .Utils import *

from .Config import TkTermConfig
from .Interpreter import Interpreter
from .Redirect import Redirect
from backend.KThread import KThread

import traceback

class TerminalWidget(tk.Frame):

    SHELL_MAPPINGS = Interpreter.MAPPINGS

    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)

        self.parent = parent

        self.basename = ""
        self.commandIndex = -1
        self.commandHistory = []

        # get the root after
        self.after = self.winfo_toplevel().after

        self.currentInterpreter = None

        self.TerminalColors = TkTermConfig.get_config()

        self.caretHandling = False
        self.pendingKeys = ""

        self.icon = None

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

        self.stdout = Redirect(self, stream="stdout")
        self.stderr = Redirect(self, stream="stderr")

        self.frameScrollbar = Frame(self.frameTerminal, borderwidth=0, width=14, bg=self.TerminalColors["bg"])
        # tell frame not to let its children control its size
        self.frameScrollbar.pack_propagate(0)

        self.scrollbar = ttk.Scrollbar(self.frameScrollbar, style="Terminal.Vertical.TScrollbar", orient="vertical")
        self.scrollbar.pack(anchor=E, side=RIGHT, fill=Y, expand=True, padx=(0,3))

        self.TerminalScreen['yscrollcommand'] = self.scrollbar.set
        self.scrollbar['command'] = self.TerminalScreen.yview

        self.scrollTimer = 0
        self.frameScrollbar.bind("<Enter>", self.on_scrollbar_enter)
        self.frameScrollbar.bind("<Leave>", self.on_scrollbar_leave)

        # Initially map as leave event
        self.frameScrollbar.bind("<Map>", self.on_scrollbar_leave)

        # Flag to indicate if user enters scrollbar area
        self.isScrollbarEnterEvent = False

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
        self.shellComboBox['values'] = list(Interpreter.MAPPINGS.keys())

        # Set default shell
        self.shellComboBox.set(Interpreter.DEFAULT_SHELL)

        self.shellComboBox.bind("<<ComboboxSelected>>", self.update_shell)
        # self.shellComboBox.bind("<Button-1>", self.do_leftClick)
        self.shellComboBox.bind("<Escape>", self.do_leftClickRelease, add="+")


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
        self.TerminalScreen.pack(side=LEFT, fill=BOTH, expand=True, padx=(4,0), pady=(4,0))

        ########################################################################
        ## Key bindings
        ########################################################################
        self.TerminalScreen.bind('<MouseWheel>', self.rollWheel)
        self.frameScrollbar.bind('<MouseWheel>', self.rollWheel)
        self.scrollbar.bind('<MouseWheel>', self.rollWheel)

        self.TerminalScreen.bind('<Control-c>', self.do_cancel)
        self.TerminalScreen.bind("<Control-t>", lambda e: self.event_generate("<<eventNewTab>>") or "break")
        self.TerminalScreen.bind('<Control-Tab>', lambda e: self.event_generate("<<eventCycleNextTab>>") or "break")

        if os.name == "nt":
            self.TerminalScreen.bind('<Shift-Tab>', lambda e: self.event_generate("<<eventCyclePrevTab>>") or "break")
        else:
            self.TerminalScreen.bind('<ISO_Left_Tab>', lambda e: self.event_generate("<<eventCyclePrevTab>>") or "break")

        self.bind_keys()

        # Bind all other key press
        self.TerminalScreen.bind("<KeyPress>", self.do_keyPress)

        self.insertionIndex = self.TerminalScreen.index("end")
        self.count = 0

        self.terminalThread = None
        self.processTerminated = False

        # Caret handling and multiline commands
        self.multilineCommand = ""

        # Automatically set focus to Terminal screen when initialised
        self.TerminalScreen.focus_set()

    def terminate(self):
        """ Terminate this terminal instance """

        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):
            self.TerminalScreen.event_generate("<Control-c>")
            self.stdout = sys.stdout
            self.stderr = sys.stderr

            self.check_process_terminate()

    def check_process_terminate(self):

        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):
            self.after(100, self.check_process_terminate)


    def reset(self):

        # Caret handling and multiline commands
        self.multilineCommand = ""
        self.caretHandling = False

    def set_color_style(self):
        """
        Set coloring style for widgets
        """

        TerminalColors = TkTermConfig.get_config()

        self.TerminalScreen["bg"]               = TerminalColors["bg"]
        self.TerminalScreen["fg"]               = TerminalColors["fg"]
        self.TerminalScreen["selectbackground"] = TerminalColors["selectbackground"]

        self.frameTerminal["bg"] = TerminalColors["bg"]
        self.frameScrollbar["bg"] = TerminalColors["bg"]

        ########################################################################
        ## Font
        ########################################################################

        terminalFont = Font(family=TerminalColors["fontfamily"], size=TerminalColors["fontsize"])
        self.TerminalScreen["font"] = terminalFont

        boldFont = Font(font=terminalFont)
        boldFont.configure(weight="bold")

        self.TerminalScreen.tag_config("basename", foreground=TerminalColors["basename"], font=boldFont)
        self.TerminalScreen.tag_config("error", foreground=TerminalColors["error"])
        self.TerminalScreen.tag_config("output", foreground=TerminalColors["output"])

        ########################################################################
        ## Scrollbar
        ########################################################################

        self.style.configure("Terminal.Vertical.TScrollbar", troughcolor=TerminalColors["bg"])
        self.style.configure("Terminal.Vertical.TScrollbar", arrowcolor=TerminalColors["bg"])

        self.style.map('Terminal.Vertical.TScrollbar',
            background=[
                ('pressed', "#9DA5B4"),
                ('disabled', TerminalColors["bg"])
            ],
            arrowcolor=[
                ('disabled', TerminalColors["bg"]),
                ('active', TerminalColors["bg"])
            ]
        )

        ########################################################################
        ## Shell selection combobox
        ########################################################################

        self.style.map('Shell.TCombobox', background=[('hover', "#2F333D")])
        self.style.map('Shell.TCombobox', fieldbackground=[('hover', "#2F333D")])
        self.style.map('Shell.TCombobox', arrowcolor=[('readonly', '#9DA5B4')])

        self.style.configure("Shell.TCombobox", fieldbackground="#21252B") # current field background
        self.style.configure("Shell.TCombobox", background="#21252B") # arrow box background
        self.style.configure("Shell.TCombobox", foreground="#9DA5B4") # current field foreground

        ########################################################################
        ## Status bar
        ########################################################################

        self.statusLabel["bg"] = "#21252B"
        self.statusLabel["fg"] = "#9DA5B4"

        # Use i-beam cursor
        if TerminalColors["cursorshape"] == "bar":
            self.TerminalScreen['blockcursor'] = False
            self.TerminalScreen['insertwidth'] = 1

        # Use block cursor
        elif TerminalColors["cursorshape"] == "block":
            self.TerminalScreen['blockcursor'] = True
            self.TerminalScreen['insertwidth'] = 0


    def on_scrollbar_enter(self, event):
        """
        On focus on scrollbar increase width of scrollbar
        """

        self.isScrollbarEnterEvent = True

        # self.style.configure("Terminal.Vertical.TScrollbar",
        #     width=10,
        #     arrowsize=10
        # )

        self._scrollbar_animation()

    def on_scrollbar_leave(self, eventL):
        """
        On focus off from scrollbar decrease width of scrollbar
        """

        self.isScrollbarEnterEvent = False

        # self.style.configure("Terminal.Vertical.TScrollbar",
        #     width=5,

        #     # hack to make arrow invisible
        #     arrowsize=-10
        # )

        self._scrollbar_animation()

    def _scrollbar_animation(self):

        if self.isScrollbarEnterEvent:
            self.scrollTimer += 3

            if self.scrollTimer <= 12:
                self.after(100, self._scrollbar_animation)
            else:
                self.style.configure("Terminal.Vertical.TScrollbar", arrowsize=10)
                self.style.map('Terminal.Vertical.TScrollbar',
                    background=[('active', "#9DA5B4"), ('pressed', "#9DA5B4"), ('disabled', TkTermConfig.CONFIG["bg"])]
                )
                self.style.configure("Terminal.Vertical.TScrollbar", background="#9DA5B4")

        else:
            self.scrollTimer -= 1

            if self.scrollTimer >= 0:
                self.after(100, self._scrollbar_animation)
            else:
                self.style.configure("Terminal.Vertical.TScrollbar", arrowsize=-10)
                self.style.configure("Terminal.Vertical.TScrollbar", width=5)
                self.style.map('Terminal.Vertical.TScrollbar',
                    background=[('active', "#3A3E48"), ('disabled', TkTermConfig.CONFIG["bg"])]
                )
                self.style.configure("Terminal.Vertical.TScrollbar", background="#3A3E48")

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

    def update_shell(self, print_basename=True, *args):

        # Update current interpreter
        self.currentInterpreter = Interpreter.get_interpreter(self.shellComboBox.get())
        self.shellComboBox.selection_clear()
        self.TerminalScreen.focus()

        # Update icon
        self.icon = Interpreter.get_icon(self.shellComboBox.get())

        # Generate event
        self.event_generate("<<eventUpdateShell>>")

        if print_basename:
            # When new shell is selected from the list we want to add new line
            # and print basename in case the prompt changes
            self.insert_new_line()
            self.print_basename()

    def do_cancel(self, *args):

        import signal

        # Kill current running process if there is any
        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):

            # Signals TerminalPrint to immediately stops any printout
            self.processTerminated = True

            self.stdout.write("^C")

            (stdout, stderr) = self.currentInterpreter.terminate(self.terminalThread.process)

            self.stdout.write(stdout, end='')
            self.stderr.write(stderr, end='')

        else:

            # Clear multiline commands
            if self.multilineCommand != "":
                self.multilineCommand = ""

            if self.caretHandling:
                # Always clear caret handle
                self.caretHandling = False

            # Clear commands
            self.insert_new_line()
            self.print_basename()

    class TerminalPrint(KThread):

        def __init__(self, top, cmd):

            KThread.__init__(self)
            # super().__init__(parent, *args, **kwargs)

            self.daemon = True
            self.cmd = cmd
            self.returnCode = 0

            self.process = None

            # Attach outer class instance
            self.top = top

        def run(self):

            # Modify shell executable based on selected shell combobox variable
            shellSelected = self.top.shellComboBox.get()

            # Set current interpreter based on shell selected
            # self.top.currentInterpreter = Interpreter.get_interpreter(shellSelected)

            if self.cmd != "":

                try:

                    # with subprocess.Popen(self.cmd, **process_options) as self.process:
                    with self.top.currentInterpreter.execute(self.cmd) as self.process:

                        # if hasattr(self.process, "stdout") and hasattr(self.process, "stderr"):
                        for line in self.process.stdout:

                            # if self.top.processTerminated:
                            #     break

                            self.top.stdout.write(line, end='')

                        for line in self.process.stderr:
                            self.top.stderr.write(line, end='')


                    self.returnCode = self.top.currentInterpreter.get_return_code(self.process)

                except Exception:
                    self.top.stderr.write(traceback.format_exc())
                    self.returnCode = -1

            # Always print basename on a newline
            insert_pos = self.top.TerminalScreen.index("insert")
            if insert_pos.split('.')[1] != '0':
                self.top.insert_new_line()

            self.top.print_basename()
            self.top.processTerminated = False

    def clear_screen(self):
        """ Clear screen and print basename """

        self.TerminalScreen.delete("1.0", END)
        self.print_basename()

    def print_basename(self):
        """ Print basename on Terminal """

        self.stdout.write(self.get_basename(), end='')
        self.stdout.write(self.pendingKeys, end='')

        self.pendingKeys = ""

    def get_basename(self):
        """ Get full basename comtaining newline characters """

        if self.caretHandling:
            return "> "
        else:
            return self.currentInterpreter.get_prompt()

    def get_last_basename(self):
        """ Get the basename after the last newline character """

        basename = self.get_basename()

        if "\n" in basename:
            return basename.split("\n")[-1]

        return basename


    def do_keyHome(self, *args):
        """ Press HOME to return to the start position of command """

        pos = self.get_pos_after_basename()

        self.TerminalScreen.mark_set("insert", pos)
        return "break"

    def get_pos_after_basename(self):
        """ Return starting position of the command """

        pos = get_last_line(self.TerminalScreen)
        pos_integral = str(pos).split('.')[0]
        offset = '.' + str(len(self.get_last_basename()))
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

            self.stdout.write(return_cmd, end='')

        # Also print the files and folders that matched the pattern only if
        # the results have more than one entry
        if len(cd_children) > 1:
            self.insert_new_line()
            self.stdout.write('\n'.join(cd_children))

            self.print_basename()
            self.stdout.write(return_cmd, end='')

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
        cmd = cmd.strip()

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

            # Set caret handling
            if not self.caretHandling:
                self.caretHandling = True

            self.insert_new_line()
            self.print_basename()

        # Valid command
        else:

            # Add to command history
            if cmd in self.commandHistory:
                self.commandHistory.pop(self.commandIndex)

            self.commandIndex = -1
            self.commandHistory.insert(0, cmd)

            # Merge all multiline command and disable caret handling
            if self.multilineCommand != "":
                cmd = self.multilineCommand + cmd
                self.multilineCommand = ""

                self.caretHandling = False

            if cmd == "clear" or cmd == "reset":
                self.clear_screen()

            elif "cd" in cmd.split()[0]:
                path = ' '.join(cmd.split()[1:])
                path = os.path.expanduser(path)

                if os.path.isdir(path):
                    os.chdir(path)

                    # Insert new line
                    self.insert_new_line()
                    self.set_returnCode(0)
                else:
                    self.insert_new_line()
                    self.stderr.write("cd: no such file or directory: {}".format(path))
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

        if int(str(index).split('.')[1]) >= len(self.get_last_basename()):
            self.TerminalScreen.delete(index)

        return "break"

    def do_keyLeftArrow(self, *args):
        """ Moves cursor to the left until it reaches the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) < len(self.get_last_basename()):
            return "break"

    def do_keyUpArrow(self, *args):
        """ Press UP arrow to get previous command in history """

        if self.commandIndex < len(self.commandHistory) - 1:
            self.commandIndex += 1

            self.delete_cmd()

            cmd = self.commandHistory[self.commandIndex]
            self.stdout.write(cmd, end='')

        return 'break'

    def do_keyDownArrow(self, *args):
        """ Press Down arrow to get the next command in history """

        if self.commandIndex >= 1:
            self.commandIndex -= 1

            self.delete_cmd()

            cmd = self.commandHistory[self.commandIndex]
            self.stdout.write(cmd, end='')

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
        seq2 = ["∙∙∙∙∙∙∙", "●∙∙∙∙∙∙", "∙●∙∙∙∙∙", "∙∙●∙∙∙∙", "∙∙∙●∙∙∙", "∙∙∙∙●∙∙", "∙∙∙∙∙●∙", "∙∙∙∙∙∙●"]

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

        self.stdout.write(cmd, end='')
        self.do_keyReturn()