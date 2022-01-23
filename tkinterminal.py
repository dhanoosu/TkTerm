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

    def __init__(self, widget, autoscroll=True):
        self.widget = widget
        self.autoscroll = autoscroll
    def write(self, text):

        self.widget.insert("end", text)

        if self.autoscroll:
            self.widget.see("end")

class App(tk.Tk):
    def __init__(self, master):
        # super().__init__()
        self.master = master
        self.after = master.after

        self.frameTerminal = tk.Frame(master, borderwidth=0)

        self.Terminal = tk.Text(self.frameTerminal, bg="black", fg="white", insertbackground="white", highlightthickness = 0)
        self.Terminal['blockcursor'] = True

        scrollbar = ttk.Scrollbar(self.frameTerminal, orient="vertical")

        self.Terminal['yscrollcommand'] = scrollbar.set
        scrollbar['command'] = self.Terminal.yview
        scrollbar.pack(side=RIGHT, fill=Y)

        self.frameStatusBar = tk.Frame(master, borderwidth=0)

        self.returnCodeLabel = Label(self.frameStatusBar, text="RC: 0", fg="white", bg="green")
        self.returnCodeLabel.pack(side=LEFT)

        self.statusText = StringVar()
        self.statusText.set("Status: IDLE")
        self.statusLabel = Label(self.frameStatusBar, textvariable=self.statusText)
        self.statusLabel.pack(side=LEFT)

        self.frameStatusBar.pack(side=BOTTOM, fill=X)
        self.frameTerminal.pack(side=TOP, fill=BOTH, expand=True)
        self.Terminal.pack(side=LEFT, fill=BOTH, expand=True)

        self.Terminal.bind("<Return>", self.do_return)
        self.Terminal.bind("<Up>", self.do_upArrow)
        self.Terminal.bind("<Down>", self.do_downArrow)
        self.Terminal.bind("<BackSpace>", self.do_backspace)
        self.Terminal.bind("<Left>", self.do_leftArrow)
        self.Terminal.bind('<Button-1>', self.do_click)
        self.Terminal.bind('<ButtonRelease-1>', self.do_clickRelease)
        self.Terminal.bind('<Tab>', self.do_tab)
        self.Terminal.bind('<Home>', self.do_home)
        self.Terminal.bind('<Control-c>', self.kill_process)

        self.index = None
        self.count = 0;

        self.terminalThread = None

    def kill_process(self, *args):

        if (self.terminalThread is not None) and (self.terminalThread.is_alive()):
            if (os.name == 'nt'):
                subprocess.Popen("TASKKILL /F /PID {pid} /T".format(pid=self.terminalThread.current_thread.pid))
            else:
                self.terminalThread.current_thread.kill()


    class TerminalPrint(threading.Thread):

        def __init__(self, cmd):
            threading.Thread.__init__(self)
            self.daemon = True
            self.cmd = cmd
            self.returnCode = 0

            self.current_thread = None


        def run(self):

            stdin = subprocess.PIPE

            process_options = {
                "shell"                 : True,
                "stdout"                : subprocess.PIPE,
                "stderr"                : subprocess.STDOUT,
                "universal_newlines"    : True,
                # "executable"            : "/bin/csh",
                "cwd"                   : os.getcwd()
            }

            if self.cmd is not "":

                if (os.name != 'nt'): self.cmd = "exec " + self.cmd

                self.current_thread =  subprocess.Popen(self.cmd, **process_options)

                while True:
                    output = self.current_thread.stdout.readline()
                    rc = self.current_thread.poll()
                    if output == '' and rc is not None:
                        break

                    if output:
                        print(output, end='')

                self.current_thread = None

                self.returnCode = rc


            global basecmd
            basecmd = os.getcwd() + ">> "
            print(basecmd, end='')


    def clear_screen(self):
        self.Terminal.delete("1.0", END)
        self.print_basecmd()

    def print_basecmd(self):
        global basecmd
        print(basecmd, end='')

    def set_basecmd(self, text):

        global basecmd
        basecmd = text + ">> "

    def do_home(self, *args):

        pos = get_last_line(self.Terminal)
        pos = str(pos).split('.')[0]
        offset = '.' + str(len(basecmd))
        new_pos = pos + offset

        self.Terminal.mark_set("insert", new_pos)
        return "break"

    def get_pos_before_cmd(self):
        # Get cmd position
        pos = get_last_line(self.Terminal)
        pos_integral = str(pos).split('.')[0]
        offset = '.' + str(len(basecmd))
        new_pos = pos_integral + offset

        return new_pos

    def do_tab(self, *args):
        """ Tab completion """

        # Windows use backward slash
        # Uninx uses forward slash
        slash = os.sep

        new_pos = self.get_pos_before_cmd()

        raw_cmd = self.Terminal.get(new_pos, "end-1c")
        cmd = raw_cmd

        if cmd == "":
            last_cmd = ""
        elif cmd[-1] == " ":
            last_cmd = ""
        else:
            last_cmd = cmd.split()[-1]

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

        if common_path != "":
            self.Terminal.delete(new_pos, END)
            return_cmd += common_path[len(last_cmd):]

            # if len(cd_children) == 1:
            #     return_cmd += ' '

            print(return_cmd, end='')

        if len(cd_children) > 1:
            self.insert_new_line()
            print('\n'.join(cd_children))

            self.print_basecmd()
            print(return_cmd, end='')


        return "break"

    def do_clickRelease(self, *args):

        self.Terminal.mark_set("insert", self.index)

    def do_click(self, *args):

        self.index = self.Terminal.index("insert")
        self.Terminal.mark_set("insert", self.index)
        # return "break"

    def do_return(self, *args):

        new_pos = self.get_pos_before_cmd()

        cmd = self.Terminal.get(new_pos, "end-1c").strip()

        if cmd == "":
            self.insert_new_line()
            self.print_basecmd()
            pass
        elif cmd == "clear":
            self.clear_screen()
        elif "cd" in cmd.split()[0]:
            path = ''.join(cmd.split()[1:])
            path = os.path.abspath(path)

            if os.path.exists(path):
                os.chdir(path)
                self.set_basecmd(path)
                self.insert_new_line()
                self.set_returnCode(0)
            else:
                self.insert_new_line()
                print("\"{}\": No such file or directory.".format(path))
                self.set_returnCode(1)

            self.print_basecmd()
        else:
            self.insert_new_line()

            self.terminalThread = self.TerminalPrint(cmd)
            self.terminalThread.start()

            self.count = 0
            self.monitor(self.terminalThread)


        return 'break'

    def do_backspace(self, *args):

        global basecmd

        index = self.Terminal.index("insert-1c")

        if int(str(index).split('.')[1]) < len(basecmd):
            return "break"

    def do_leftArrow(self, *args):

        global basecmd

        index = self.Terminal.index("insert-1c")

        if int(str(index).split('.')[1]) < len(basecmd):
            return "break"


    def do_upArrow(self, *args):
        return 'break'

    def do_downArrow(self, *args):
        return 'break'


    def insert_new_line(self):

        self.Terminal.insert(END, "\n")

    def monitor(self, progress_thread):

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

        if(rc != 0):
            self.returnCodeLabel.configure(bg="red")
        else:
            self.returnCodeLabel.configure(bg="green")

        self.returnCodeLabel['text'] = "RC: {}".format(rc)



if __name__ == "__main__":

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    root=tk.Tk()
    root.geometry("700x400")

    app = App(root)

    sys.stdout = Redirect(app.Terminal)
    sys.stderr = Redirect(app.Terminal)

    basecmd = os.getcwd() + ">> "

    print(basecmd, end='')

    root.mainloop()

    sys.stdout = old_stdout
    sys.stderr = old_stderr