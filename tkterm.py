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
from src.Interpreter import Interpreter
from src.Config import TkTermConfig

class Terminal(tk.Frame):

    """ Terminal widget """

    def __init__(self, parent, text=None, init=True, *args, **kwargs):

        super().__init__(parent, *args, **kwargs)

        self.init = init
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
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=BOTH)
        self.notebook.bind("<B1-Motion>", self._reorder_tab)
        self.notebook.bind("<ButtonRelease-2>", self._close_tab)
        self.notebook.bind("<<NotebookTabChanged>>", self._insert_tab)

        self.terminalTabs = []

        # Add default tabs
        # This will automatically create a tab and an add tab button
        self.icon = PhotoImage(file=get_absolute_path(__file__, "./img", "plus.png"))
        self.notebook.add(tk.Frame(self), image=self.icon)

        # Set color profile for notebook
        self.init_style()

        self.parent = parent
        # self.parent.bind("<Configure>", self.on_resize)

    def add_interpreter(self, *args, **kwargs):
        """ Add a new interpreter and optionally set as default """

        Interpreter.add_interpreter(*args, **kwargs)

    def _insert_tab(self, *event):
        """ Insert new tab event """

        # Fake the last tab as insert new tab
        if self.notebook.select() == self.notebook.tabs()[-1]:
            terminal = App(self)

            if self.splashText:
                terminal.update_shell(print_basename=False)
                terminal.stdout.write(self.splashText)

            terminal.update_shell()

            # Attach search bar to terminal
            terminal.searchBar = SearchBar(terminal)

            # Attach right click context menu
            terminal.contextMenu = RightClickContextMenu(self, terminal)

            # Insert new tab before the add button
            index = len(self.notebook.tabs()) - 1
            self.notebook.insert(index, terminal, text=f"Terminal {len(self.notebook.tabs())}", image=terminal.icon, compound=LEFT)
            self.notebook.select(index)

            tab_id = self.notebook.select()
            terminal.bind("<<updateShell>>", lambda event: self._update_icon(tab_id))

    def _update_icon(self, tab_id):

        terminal = self.notebook.nametowidget(tab_id)
        self.notebook.tab(tab_id, image=terminal.icon)

    def _reorder_tab(self, event):
        """ Drag to reorder tab """

        try:
            index = self.notebook.index(f"@{event.x},{event.y}")

            if index >= len(self.notebook.tabs()) - 1:
                return

            self.notebook.insert(index, child=self.notebook.select())

        except tk.TclError:
            pass

    def _close_tab(self, event):
        """ Close tab event """

        try:

            index = self.notebook.index(f"@{event.x},{event.y}")

            # Do nothing if it is the last tab (add tab button)
            if index >= len(self.notebook.tabs()) - 1:
                return

            # Do nothing if there are 2 tabs left
            if len(self.notebook.tabs()) == 2:
                return

            # When closing the last tab, immediately switch to the tab before
            if index == len(self.notebook.tabs()) - 2:
                self.notebook.select(len(self.notebook.tabs()) - 3)

            app = self.notebook.nametowidget(self.notebook.tabs()[index])

            # TODO: Error on closing tabs if there are processes running
            # If process still running just kill it
            app.terminate()

            del app.searchBar
            del app.contextMenu

            for child in app.winfo_children():
                child.destroy()

            app.destroy()

            # self.notebook.event_generate("<<NotebookTabClosed>>")

        except Exception:
            pass

    def set_color_style(self):

        for tab in self.notebook.tabs()[:-1]:
            app = self.notebook.nametowidget(tab)

            app.set_color_style()

        self.init_style()

    def on_resize(self, event):
        """Auto scroll to bottom when resize event happens"""

        first_visible_line = self.TerminalScreen.index("@0,0")

        if self.scrollbar.get()[1] >= 1:
            self.TerminalScreen.see(END)
        # elif float(first_visible_line) >  1.0:
        #     self.TerminalScreen.see(float(first_visible_line)-1)

        # self.statusText.set(self.TerminalScreen.winfo_height())

    def init_style(self):
        """ Style the notebook """

        s = ttk.Style()
        s.theme_use('default')
        s.configure('Terminal.TNotebook',
            background="#414755",
            bd=0,
            borderwidth=0,
            padding=[0,0,0,0],
            tabmargins=[7, 7, 50, 0],
            # tabposition='wn'
        )

        s.configure('Terminal.TNotebook.Tab',
            borderwidth=0,
            padding=[10,5],
            # width=15,
            height=1,
            background="#495162",
            foreground="#9da5b4",
            font=('Helvetica','8'),
            focuscolor=TkTermConfig.get_config("bg")
        )

        s.map("Terminal.TNotebook.Tab",
            background=[("selected", TkTermConfig.get_config("bg")), ("active", TkTermConfig.get_config("bg"))],
            foreground=[("selected", "white"), ("active", "white")],
            font=[("selected", ('Helvetica 8 bold'))],
            # expand=[("selected", [0, 3])]
        )

        self.notebook.configure(style="Terminal.TNotebook")


if __name__ == "__main__":

    root = tk.Tk()
    root.title("TkTerm - Terminal Emulator")
    root.geometry("700x400")


    terminal = Terminal(root)
    terminal.pack(expand=True, fill=BOTH)

    # root.iconbitmap(default='icon.png')

    photo = PhotoImage(file="icon.png")
    root.iconphoto(False, photo)
    root.update()
    root.mainloop()