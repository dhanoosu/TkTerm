import tkinter as tk
import tkinter.messagebox

from tkinter import *
from tkinter import ttk

from tkinter import colorchooser
from tkinter import font
from tkinter.font import Font

import threading
import io
import os
import sys
import subprocess
import time
import json

# Add to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.InterpreterShell import InterpreterShell

from src.TerminalScreen import App
from src.Utils import *
from src.Redirect import Redirect
from src.RightClickContextMenu import RightClickContextMenu
from src.SearchBar import SearchBar

# Configuration filename
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "tkterm_settings.json")

class TerminalTab(ttk.Notebook):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.pack(expand=True, fill=BOTH)

        self.enable_traversal()

        self.tabs = []

        self._add_tab("Terminal 1")
        self._add_tab("+")

        self.bind("<B1-Motion>", self._reorder)

    def init_style(self, TerminalColors):

        s = ttk.Style()
        s.theme_use('default')
        s.configure('Terminal.TNotebook',
            background="#2f333d",
            bd=0,
            borderwidth=0,
            padding=[0,0,0,0],
            tabmargins=[5, 5, 5, 0],
            # tabposition='wn'
        )

        s.configure('Terminal.TNotebook.Tab',
            borderwidth=0,
            padding=[5,5],
            width=10
        )

        s.map("Terminal.TNotebook.Tab",
            background=[("selected", TerminalColors["bg"]), ("active", TerminalColors["bg"])],
            foreground=[("selected", "white"), ("active", "white")]
        )

        self.configure(style="Terminal.TNotebook")


    def _add_tab(self, name):

        new_tab = tk.Frame(self, bd=0, relief=FLAT)
        new_tab.pack(expand=True, fill=BOTH)

        self.tabs.append(new_tab)

        self.add(self.tabs[-1], text=name)


    def _reorder(self, event):

        try:
            index = self.index(f"@{event.x},{event.y}")
            self.insert(index, child=self.select())

        except tk.TclError:
            pass

class Terminal(App):

    """ Terminal widget """

    def __init__(self, parent, text=None, init=True, *args, **kwargs):

        old_stdout = sys.stdout
        old_stderr = sys.stderr

        # Current interpreter
        self.INTERPRETER = InterpreterShell(None)

        # List of interpreter backends
        self.INTERPRETER_BACKENDS = {}

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

        # Load settings from file
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)

                for k in data.keys():
                    if k in self.TerminalColors.keys():
                        self.TerminalColors[k] = data[k]

        try:

            # Create tabbed terminal
            # terminalTab = TerminalTab(parent)
            # terminalTab.init_style(self.TerminalColors)


            # Initialise super classes
            # super().__init__(terminalTab.tabs[0], *args, **kwargs)
            # super().__init__(terminalTab.tabs[1], *args, **kwargs)

            super().__init__(parent, *args, **kwargs)

            # for tab in terminalTab.tabs:
            #     a = App(tab, self.TerminalColors)
            #     self.contextMenu = RightClickContextMenu(a)

            sys.stdout = Redirect(self, stream="stdout")
            sys.stderr = Redirect(self, stream="stderr")


            self.parent = parent
            self.parent.bind("<Configure>", self.on_resize)


            # Print some text before the main initialisation
            if text:
                print(text)

            # Initialisation - print the basename
            if init:
                self.print_basename()

            # Attach search bar to terminal screen
            self.searchBar = SearchBar(self.TerminalScreen)

            # Attach right-click context menu
            self.contextMenu = RightClickContextMenu(self)

        except:
            # sys.stdout = sys.__stdout__
            # sys.stderr = sys.__stderr__
            pass

    def set_current_interpreter(self, name):
        """ Set current interpreter based on shell selected """

        self.INTERPRETER = self.INTERPRETER_BACKENDS[name]

        # Update history storage binding
        self.commandHistory = self.INTERPRETER.get_history()

    def add_interpreter(self, name, interpreter, set_default=True):
        """ Add a new interpreter and optionally set as default """

        self.shellMapping[name] = None
        self.shellComboBox['values'] = list(self.shellMapping)

        self.INTERPRETER_BACKENDS[name] = interpreter

        if set_default:
            self.shellComboBox.set(name)
            self.update_shell()

    def init_interpreter(self):
        """ Initialise interpreter backends """

        self.INTERPRETER_BACKENDS.clear()

        for name in self.shellComboBox['values']:
            self.INTERPRETER_BACKENDS[name] = InterpreterShell(self.shellMapping[name])

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