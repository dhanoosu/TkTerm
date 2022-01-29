import tkinter as tk
from tkinter import *
from tkinter import ttk

import threading
import os
import subprocess

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

        # Work out if the current line is a command or output
        start_pos = get_last_line(self.TerminalScreen)
        line = self.TerminalScreen.get(start_pos, self.TerminalScreen.index("insert"))
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
        else:
            # Basename
            # does not add a newline, so start_pos does not need -1
            if text.startswith(self.app.basename):
                start_pos = get_last_line(self.TerminalScreen)
                end_pos = str(start_pos).split('.')[0] + '.' + str(len(self.app.basename))
                self.TerminalScreen.tag_add("basename", start_pos, end_pos)

            # Normal output - could be command or its output
            # needs start_pos - 1
            elif not isCmd:
                start_pos = get_last_line(self.TerminalScreen) - 1
                end_pos = self.TerminalScreen.index("insert")
                self.TerminalScreen.tag_add("output", start_pos, end_pos)



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
        self.frameTerminal = tk.Frame(self, borderwidth=0)

        self.TerminalScreen = tk.Text(self.frameTerminal, bg=self.TerminalColors["bg"], fg=self.TerminalColors["fg"], insertbackground="white", highlightthickness = 0)
        self.TerminalScreen['blockcursor'] = True

        scrollbar = ttk.Scrollbar(self.frameTerminal, orient="vertical")

        self.TerminalScreen['yscrollcommand'] = scrollbar.set
        scrollbar['command'] = self.TerminalScreen.yview
        scrollbar.pack(side=RIGHT, fill=Y)

        ########################################################################
        ## Status bar
        ########################################################################
        self.frameStatusBar = tk.Frame(self, borderwidth=0)

        self.returnCodeLabel = Label(self.frameStatusBar, text="RC: 0", fg="white", bg="green", font=("arial", 9), anchor=W, width=8)
        self.returnCodeLabel.pack(side=LEFT)

        self.statusText = StringVar()
        self.statusText.set("Status: IDLE")
        self.statusLabel = Label(self.frameStatusBar, textvariable=self.statusText, font=("arial", 9))
        self.statusLabel.pack(side=LEFT)


        self.shellMapping = {
            "csh" : "/bin/csh",
            "bash" : "/bin/sh",
            "windows" : None
        }

        self.shellComboBox = ttk.Combobox(self.frameStatusBar, state="readonly")
        self.shellComboBox.pack(side=RIGHT)
        self.shellComboBox['values'] = list(self.shellMapping)

        self.shellComboBox.bind("<<ComboboxSelected>>", self.update_shell)

        # Need to pack these last otherwise a glitch happens
        # where scrollbar disappear when window resized
        self.frameStatusBar.pack(side=BOTTOM, fill=X)
        self.frameTerminal.pack(side=TOP, fill=BOTH, expand=True)
        self.TerminalScreen.pack(side=LEFT, fill=BOTH, expand=True)

        ########################################################################
        ## Key bindings
        ########################################################################

        self.TerminalScreen.bind("<Return>",              self.do_return)
        self.TerminalScreen.bind("<Up>",                  self.do_upArrow)
        self.TerminalScreen.bind("<Down>",                self.do_downArrow)
        self.TerminalScreen.bind("<BackSpace>",           self.do_backspace)
        self.TerminalScreen.bind("<Left>",                self.do_leftArrow)
        self.TerminalScreen.bind('<Button-1>',            self.do_click)
        self.TerminalScreen.bind('<ButtonRelease-1>',     self.do_clickRelease)
        self.TerminalScreen.bind('<Tab>',                 self.do_tab)
        self.TerminalScreen.bind('<Home>',                self.do_home)
        self.TerminalScreen.bind('<Control-c>',           self.do_cancel)

        self.index = None
        self.count = 0;

        self.terminalThread = None

        # Sets default shell based on operating system
        if (os.name == 'nt'):
            self.shellComboBox.set("windows")
        else:
            self.shellComboBox.set("csh")


        # Automatically set focus to Terminal screen when initialised
        self.TerminalScreen.focus_set()

    def update_shell(self, *args):
        self.shellComboBox.selection_clear()
        self.TerminalScreen.focus()

    def do_cancel(self, *args):

        import signal

        # Kill current running process if there is any
        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):
            if (os.name == 'nt'):
                subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=self.terminalThread.process.pid))
            else:
                os.system("pkill -TERM -P %s" % self.terminalThread.process.pid)

                # os.killpg(os.getpgid(self.terminalThread.process.pid), signal.SIGTERM)

                self.terminalThread.process.kill()
                self.terminalThread.process.terminate()

                self.terminalThread.process.wait()

        else:
            # Clear commands
            self.insert_new_line()
            self.print_basename()


    class TerminalPrint(threading.Thread):

        def __init__(self, outer_instance, cmd):
            threading.Thread.__init__(self)
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

            # Modify shell executable based on selected shell combobox variable
            shellSelected = self.outer_instance.shellComboBox.get()
            process_options['executable'] = self.shellMapping[shellSelected]

            if self.cmd is not "":

                with subprocess.Popen(self.cmd, **process_options) as self.process:
                    for line in self.process.stdout:
                        print(line, end='')
                    for line in self.process.stderr:
                        print(line, file=sys.stderr, end='')


                # self.process =  subprocess.Popen(self.cmd, **process_options)
                # while True:
                #     output = self.process.stdout.readline()
                #     rc = self.process.poll()
                #     if output == '' and rc is not None:
                #         break

                #     if output:
                #         print(output, end='')


                rc = self.process.poll()
                self.process = None
                self.returnCode = rc

            self.outer_instance.set_basename(os.getcwd())
            self.outer_instance.print_basename()

    def clear_screen(self):
        self.TerminalScreen.delete("1.0", END)
        self.print_basename()

    def print_basename(self):
        print(self.basename, end='')

    def set_basename(self, text):

        if text.endswith(" "):
            text = text.rstrip()

        self.basename = text + ">> "

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

        self.TerminalScreen.mark_set("insert", self.index)

    def do_click(self, *args):

        self.index = self.TerminalScreen.index("insert")
        self.TerminalScreen.mark_set("insert", self.index)
        # return "break"

    def do_return(self, *args):

        cmd = self.get_cmd()

        # Empty command - pass
        if cmd == "":
            self.insert_new_line()
            self.print_basename()
            pass

        # Command not empty
        else:

            if cmd in self.commandHistory:
                self.commandHistory.pop(self.commandIndex)

            self.commandIndex = -1
            self.commandHistory.insert(0, cmd)

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
                self.monitor(self.terminalThread)


        return 'break'

    def do_backspace(self, *args):
        """ Delete a character until the basename """

        index = self.TerminalScreen.index("insert-1c")

        if int(str(index).split('.')[1]) < len(self.basename):
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

    def set_returnCode(self, rc):
        """ Set return code on status bar """

        if(rc != 0):
            self.returnCodeLabel.configure(bg="red")
        else:
            self.returnCodeLabel.configure(bg="green")

        self.returnCodeLabel['text'] = "RC: {}".format(rc)

    def run_command(self, cmd):
        """ Print and execute command on terminal """

        print(cmd, end='')
        self.do_return()


class Terminal(App):

    """ Terminal widget """

    def __init__(self, parent, *args, **kwargs):

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        self.TerminalColors = {
            "fg" : "#E6E6E6",
            "bg" : "#1F1E1E"
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


    def on_resize(self, *args):
        """Auto scroll to bottom when resize event happens"""
        self.TerminalScreen.see(END)

if __name__ == "__main__":

    root = tk.Tk()
    root.title("TkTerm - Terminal Emulator")
    root.geometry("700x400")

    terminal = Terminal(root)
    terminal.pack(expand=True, fill='both')

    root.mainloop()