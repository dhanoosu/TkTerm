import tkinter as tk
from tkinter import *
from tkinter import ttk

from tkinter import font
from tkinter.font import Font

import os
import sys
import json

# Add to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.TerminalTab import TerminalTab
from src.Interpreter import Interpreter
from src.ExitDiaglogBox import ExitDiaglogBox
from src.Utils import get_absolute_path
from src.Config import TkTermConfig

class Terminal(tk.Frame):

    """ Terminal widget """

    def __init__(self, parent, text=None, *args, **kwargs):

        super().__init__(parent, *args, **kwargs)

        self.splashText = text

        # Initialised all interpreter backends
        Interpreter.init_backends()

        ########################################################################
        # Load setting profile
        ########################################################################
        self.TerminalConfig = TkTermConfig.get_default()

        if "Cascadia Code SemiLight" in font.families():
            self.TerminalConfig["fontfamily"] = "Cascadia Code SemiLight"
        else:
            self.TerminalConfig["fontfamily"] = "Consolas"

        TkTermConfig.set_default(self.TerminalConfig)

        # Load settings from file
        if os.path.isfile(TkTermConfig.CONFIG_FILE):
            with open(TkTermConfig.CONFIG_FILE, "r") as f:
                try:
                    data = json.load(f)

                    for k in data.keys():
                        if k in self.TerminalConfig.keys():
                            self.TerminalConfig[k] = data[k]
                except:
                    pass

        TkTermConfig.set_config(self.TerminalConfig)

        ########################################################################
        # Create terminal tabs using notebook
        ########################################################################
        self.notebook = TerminalTab(self, self.splashText)
        self.notebook.pack(expand=True, fill=BOTH)

    def add_interpreter(self, *args, **kwargs):
        """ Add a new interpreter and optionally set as default """

        Interpreter.add_interpreter(*args, **kwargs)

    def run_command(self, cmd):
        """ Run command on current terminal tab """

        # Get the selected tab
        tab_id = self.notebook.select()

        # Get the associated terminal widget
        terminal = self.notebook.nametowidget(tab_id)
        terminal.run_command(cmd)

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

    terminal = Terminal(root)
    terminal.pack(expand=True, fill=BOTH)

    icon = PhotoImage(file=get_absolute_path(__file__, "icon.png"))
    root.iconphoto(False, icon)

    ExitDiaglogBox(root, icon)
    root.mainloop()