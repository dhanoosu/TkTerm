import tkinter as tk

from tkinter import *
from tkinter import ttk

from .Utils import *

class Redirect():
    """ Redirect stdout and stderr to be written to Text widget """

    def __init__(self, widget, autoscroll=True, stream="stdout"):
        self.app = widget
        self.TerminalScreen = widget.TerminalScreen
        self.autoscroll = autoscroll
        self.stream = stream

    def write(self, text, end="\n"):

        text = text + end

        # Keep line limit for Terminal to 5000 lines
        limit_diff = int(get_last_line(self.TerminalScreen)) - 5000
        for i in range(limit_diff):
            self.TerminalScreen.delete("1.0", "2.0")

        # Work out if the current line is a command or output
        start_pos = get_last_line(self.TerminalScreen)
        line = self.TerminalScreen.get(start_pos, END)
        isCmd = True if line.startswith(self.app.get_last_basename()) else False

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
                self.app.caretHandling = False

        # Normal output
        else:
            # Basename
            if text.startswith(self.app.get_basename()):

                # Handle custom basename that contains newlines characters
                last_line_pos = get_last_line(self.TerminalScreen)

                # Start position needs to minus the number of newline characters found
                start_pos = last_line_pos - text.count("\n")
                end_pos = str(last_line_pos).split('.')[0] + '.' + str(len(self.app.get_last_basename()))

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