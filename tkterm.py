import tkinter as tk
from tkinter import *
from tkinter import ttk

import threading
import os
import subprocess
import time

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

        # Normal output
        elif not self.app.caretHandling:
            # Basename
            # does not add a newline, so start_pos does not need -1
            if text.startswith(self.app.basename):
                start_pos = get_last_line(self.TerminalScreen)
                end_pos = str(start_pos).split('.')[0] + '.' + str(len(self.app.basename))
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
        # super().__init__()
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
            insertwidth=0,
            selectbackground="#464E5E",
            undo=False
        )

        self.TerminalScreen['blockcursor'] = True

        self.frameScrollbar = Frame(self.frameTerminal, borderwidth=0, width=14, bg=self.TerminalColors["bg"])
        # tell frame not to let its children control its size
        self.frameScrollbar.pack_propagate(0)

        self.scrollbar = ttk.Scrollbar(self.frameScrollbar, orient="vertical")
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
        self.frameStatusBar = ttk.Frame(self)

        self.returnCodeLabel = Label(self.frameStatusBar, text="RC: 0", fg="white", bg="green", font=("Helvetica", 8), anchor=W, width=8)
        self.returnCodeLabel.pack(side=LEFT)

        self.statusText = StringVar()
        self.statusText.set("Status: IDLE")
        self.statusLabel = Label(self.frameStatusBar, textvariable=self.statusText, font=("Helvetica", 8), bg="#21252B", fg="#9DA5B4", relief=FLAT)
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
            'fieldbackground'       : "#21252B",    # current field background
            'background'            : '#21252B',    # arrow box background
            'foreground'            : "#9DA5B4",    # current field foreground
            "relief"                : FLAT,
            "borderwidth"           : 0,
            "highlightthickness"    : 0
        }

        self.style = ttk.Style(self)
        self.style.theme_use('default')
        self.style.configure("TCombobox", **style_combobox)
        self.style.configure("TScrollbar",
            troughcolor=self.TerminalColors["bg"],
            background="#3A3E48",
            borderwidth=0,
            relief=FLAT,
            arrowcolor=self.TerminalColors["bg"],
        )

        self.style.map('TCombobox', background=[('hover', "#2F333D")])
        self.style.map('TCombobox', fieldbackground=[('hover', "#2F333D")])
        self.style.map('TCombobox', arrowcolor=[('readonly', '#21252B')])

        self.style.map('TScrollbar', background=[('active', "#9DA5B4"), ('pressed', "#9DA5B4"), ('disabled', self.TerminalColors["bg"])])
        self.style.map('TScrollbar', arrowcolor=[('disabled', self.TerminalColors["bg"]), ('active', self.TerminalColors["bg"])])

        self.style.configure("TFrame", background="#21252B", borderwidth=0, relief=FLAT)


        # following are style option for the drop down combobox listbox
        self.option_add('*TCombobox*Listbox*Background', '#21252B')
        self.option_add('*TCombobox*Listbox*Foreground', "#9DA5B4")
        self.option_add('*TCombobox*Listbox.font', ("Helvetica", 8))


        self.shellComboBox = ttk.Combobox(self.frameStatusBar, state="readonly", width=8, font=("Helvetica", 8))
        self.shellComboBox.pack(side=RIGHT, padx=0)
        self.shellComboBox['values'] = list(self.shellMapping)

        self.shellComboBox.bind("<<ComboboxSelected>>", self.update_shell)

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


        self.TerminalScreen.bind('<Control-c>',           self.do_cancel)
        self.bind_keys()

        # Bind all other key press
        self.TerminalScreen.bind("<KeyPress>", self.do_keyPress)

        self.pendingKeys = ""

        self.insertionIndex = self.TerminalScreen.index("end")
        self.count = 0;

        self.terminalThread = None

        # Sets default shell based on operating system
        if (os.name == 'nt'):
            self.shellComboBox.set("windows")
        else:
            self.shellComboBox.set("csh")


        self.processTerminated = False;

        # Caret handling and multiline commands
        self.multilineCommand = ""
        self.caretHandling = False
        self.oldBasename = ""

        # Automatically set focus to Terminal screen when initialised
        self.TerminalScreen.focus_set()


    def on_scrollbar_enter(self, event):


        self.style.configure("TScrollbar",
            width=10,
            arrowsize=10
        )

    def on_scrollbar_leave(self, eventL):

        self.style.configure("TScrollbar",
            width=5,
            # hack to make arrow invisible
            arrowsize=-10
        )



    def bind_keys(self):
        self.TerminalScreen.bind("<Return>",            self.do_return)
        self.TerminalScreen.bind("<Up>",                self.do_upArrow)
        self.TerminalScreen.bind("<Down>",              self.do_downArrow)
        self.TerminalScreen.bind("<BackSpace>",         self.do_backspace)
        self.TerminalScreen.bind("<Delete>",            lambda event: "")
        self.TerminalScreen.bind("<End>",               lambda event: "")
        self.TerminalScreen.bind("<Left>",              self.do_leftArrow)
        self.TerminalScreen.bind("<Right>",             lambda event: "")
        self.TerminalScreen.bind("<Button-1>",          self.do_click)
        self.TerminalScreen.bind("<ButtonRelease-1>",   self.do_clickRelease)
        self.TerminalScreen.bind("<ButtonRelease-2>",   self.do_middleClickRelease)
        self.TerminalScreen.bind("<Tab>",               self.do_tab)
        self.TerminalScreen.bind("<Home>",              self.do_home)
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
                self.set_basename(self.oldBasename, postfix="")
                self.multilineCommand = ""
                self.caretHandling = False

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

            if self.cmd is not "":

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

    def do_home(self, *args):
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

    def do_tab(self, *args):
        """ Tab completion """

        # Windows uses backward slash
        # Uninx uses forward slash
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

    def do_clickRelease(self, *args):

        self.TerminalScreen.mark_set("insert", self.insertionIndex)

    def do_middleClickRelease(self, *args):

        try:
            selected = self.TerminalScreen.selection_get()
        except Exception as e:
            selected = ""

        current_pos = self.TerminalScreen.index(INSERT)
        self.TerminalScreen.insert(current_pos, selected)

        return "break"

    def do_click(self, *args):

        self.insertionIndex = self.TerminalScreen.index("insert")
        # self.TerminalScreen.mark_set("insert", self.insertionIndex)
        # return "break"
        pass

    def do_return(self, *args):
        """ On pressing Return, execute the command """

        # Caret character differs on Windows and Unix
        CARET = "^" if (os.name == 'nt') else "\\"

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

            # Merge all multiline command and update basename to whatever
            # was previously
            if self.multilineCommand != "":
                self.set_basename(self.oldBasename, postfix="")
                cmd = self.multilineCommand + cmd
                self.multilineCommand = ""
                self.caretHandling = False

            if cmd == "clear" or cmd == "reset":
                self.clear_screen()
            elif "cd" in cmd.split()[0]:
                path = ''.join(cmd.split()[1:])
                path = os.path.abspath(path)

                if os.path.exists(path):
                    os.chdir(path)
                    self.set_basename(path)
                    self.insert_new_line()
                    self.set_returnCode(0)
                else:
                    self.insert_new_line()
                    print("\"{}\": No such file or directory.".format(path))
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

    def do_backspace(self, *args):
        """ Delete a character until the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) >= len(self.basename):
            self.TerminalScreen.delete(index)

        return "break"

    def do_leftArrow(self, *args):
        """ Moves cursor to the left until it reaches the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) < len(self.basename):
            return "break"

    def do_upArrow(self, *args):
        """ Press UP arrow to get previous command in history """

        if self.commandIndex < len(self.commandHistory) - 1:
            self.commandIndex += 1

            self.delete_cmd()

            cmd = self.commandHistory[self.commandIndex]
            print(cmd, end='')

        return 'break'

    def do_downArrow(self, *args):
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
        self.do_return()

class Terminal(App):

    """ Terminal widget """

    def __init__(self, parent, *args, **kwargs):

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        self.TerminalColors = {
            "fg" : "#E6E6E6",
            "bg" : "#282C34"
        }

        self.TerminalColors["fg"] = "green"

        super().__init__(parent, *args, **kwargs)
        parent.bind("<Configure>", self.on_resize)

        sys.stdout = Redirect(self, stream="stdout")
        sys.stderr = Redirect(self, stream="stderr")

        self.set_basename(os.getcwd())
        self.print_basename()

        self.TerminalScreen.tag_config("basename", foreground="red")
        self.TerminalScreen.tag_config("error", foreground="red")
        self.TerminalScreen.tag_config("output", foreground="#E6E6E6")

    def on_resize(self, event):
        """Auto scroll to bottom when resize event happens"""

        if self.scrollbar.get()[1] >= 1:
            self.TerminalScreen.see(END)

if __name__ == "__main__":

    root = tk.Tk()
    root.title("TkTerm - Terminal Emulator")
    root.geometry("700x400")


    terminal = Terminal(root, bg="#282C34", bd=0)
    terminal.pack(expand=True, fill='both')

    root.iconbitmap(default='icon.ico')

    root.mainloop()