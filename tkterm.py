import tkinter as tk
import tkinter.messagebox

from tkinter import *
from tkinter import ttk

from tkinter import colorchooser
from tkinter import font
from tkinter.font import Font

import os
import sys
import json

# Add to system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.InterpreterShell import InterpreterShell

from src.Utils import *
from src.TerminalScreen import TerminalWidget
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
        self.notebook.bind("<ButtonRelease-2>", lambda e: self._close_tab(event=e))
        self.notebook.bind("<<NotebookTabChanged>>", self._tab_clicked)

        self.terminalTabs = []

        # Add default tabs
        # This will automatically create a tab and an add tab button
        self.iconPlus = PhotoImage(file=get_absolute_path(__file__, "./img", "plus.png"))
        self.notebook.add(tk.Frame(self), image=self.iconPlus)

        # Set color profile for notebook
        self.init_style()

        self.parent = parent
        # self.parent.bind("<Configure>", self.on_resize)

        ########################################################################
        # Create button on notebook
        ########################################################################
        self.frameNav = tk.Frame(self)
        self.frameNav.place(rely=0, relx=1.0, x=-10, y=17, anchor="e")

        self.iconHamburger  = PhotoImage(file=get_absolute_path(__file__, "./img", "hamburger.png"))
        self.iconSearch     = PhotoImage(file=get_absolute_path(__file__, "./img", "search.png"))
        self.iconNewTab     = PhotoImage(file=get_absolute_path(__file__, "./img", "new_tab.png"))
        self.iconNextTab    = PhotoImage(file=get_absolute_path(__file__, "./img", "next_tab.png"))
        self.iconPrevTab    = PhotoImage(file=get_absolute_path(__file__, "./img", "prev_tab.png"))
        self.iconCloseTab   = PhotoImage(file=get_absolute_path(__file__, "./img", "close_tab.png"))

        self.buttonTabList = tk.Button(
            self.frameNav,
            # text="\u2630",
            image=self.iconHamburger,
            width=30,
            height=25,
            bd=0,
            relief=FLAT,
            highlightbackground="#414755",
            bg="#414755",
            fg="#9da5b4",
            activebackground="#495162",
            activeforeground="#9da5b4"
        )

        self.buttonTabList.pack()

        self.buttonTabList.bind("<ButtonRelease-1>", self._tab_menu)

        if os.name == "nt":
            self.buttonTabList.bind("<Enter>", lambda e: e.widget.config(bg="#495162"))
            self.buttonTabList.bind("<Leave>", self._tab_menu_on_leave)

    def _tab_menu_on_leave(self, event):

        if event.widget["state"] == "normal":
            event.widget.config(bg="#414755")

    def _tab_menu(self, event):

        self.tabListMenu = Menu(self,
            tearoff=0,
            bg="white",
            bd=1,
            activebackground="#2c313a",
            activeforeground="white",
            selectcolor="red",
            activeborderwidth=1,
            relief=GROOVE,
            font="Helvetica 10"
        )

        # Add list of currently opened tabs to menu
        for tab in self.notebook.tabs()[:-1]:

            self.tabListMenu.add_command(
                label="   " + self.notebook.tab(tab, option="text"),
                image=self.notebook.tab(tab, option="image"),
                compound=LEFT,
                command= lambda temp=tab: self.notebook.select(temp)
            )

        self.tabListMenu.add_separator()

        self.tabListMenu.add_command(
            label="   Search",
            accelerator="Ctrl+F",
            image=self.iconSearch, compound=LEFT,
            command=lambda : self.notebook.nametowidget(self.notebook.select()).event_generate("<Control-f>")
        )

        self.tabListMenu.add_command(
            label="   New tab",
            accelerator="Ctrl+T",
            command=self._insert_new_tab,
            image=self.iconNewTab, compound=LEFT
        )

        # Number of opened tabs (minus add tab button)
        num_tabs = len(self.notebook.tabs()) - 1

        if num_tabs == 1:
            state = "disabled"
        else:
            state = "normal"

        self.tabListMenu.add_command(
            label="   Go to next tab",
            accelerator="Ctrl+Tab",
            command=lambda: self._cycle_through_tabs(True),
            image=self.iconNextTab, compound=LEFT,
            state=state
        )

        self.tabListMenu.add_command(
            label="   Go to prev tab",
            accelerator="Shift+Tab",
            command=lambda: self._cycle_through_tabs(False),
            image=self.iconPrevTab, compound=LEFT,
            state=state
        )

        self.tabListMenu.add_command(
            label="   Close this tab",
            accelerator="Middle-click" + "{}".format("" if os.name == "nt" else "  "),
            image=self.iconCloseTab, compound=LEFT,
            command=lambda : self._close_tab(index=self.notebook.index(self.notebook.select())),
            state=state
        )

        self.tabListMenu.add_separator()

        self.tabListMenu.add_command(label="About TkTerm ...")

        self.tabListMenu.bind("<FocusOut>", lambda e: (
            e.widget.destroy(),
            event.widget.config(bg="#414755")
        ))

        try:
            event.widget.config(fg="#9da5b4", bg="#495162")
            self.tabListMenu.tk_popup(event.widget.winfo_rootx(), event.widget.winfo_rooty()+30)
            # self.tabListMenu.focus_set()
        finally:
            self.tabListMenu.grab_release()

            if os.name == "nt":
                event.widget.config(bg="#414755")

    def add_interpreter(self, *args, **kwargs):
        """ Add a new interpreter and optionally set as default """

        Interpreter.add_interpreter(*args, **kwargs)

    def _tab_clicked(self, *event):
        """ Monitor tab change event """

        # Fake the last tab as insert new tab
        if self.notebook.select() == self.notebook.tabs()[-1]:
            self._insert_new_tab()

    def _insert_new_tab(self):
        """ Insert new tab event """

        terminal = TerminalWidget(self)

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
        terminal.bind("<<eventUpdateShell>>",   lambda e : self._update_icon(tab_id))
        terminal.bind("<<eventNewTab>>",        lambda e : self._insert_new_tab())
        terminal.bind("<<eventCycleNextTab>>",  lambda e : self._cycle_through_tabs(traverse_next=True))
        terminal.bind("<<eventCyclePrevTab>>",  lambda e : self._cycle_through_tabs(traverse_next=False))

    def _cycle_through_tabs(self, traverse_next=True):
        """ Cycle through opened tabs """

        # Number of opened tabs (minus add tab button)
        num_tabs = len(self.notebook.tabs()) - 1

        # Get current tab id and its index
        tab_id = self.notebook.select()
        index = self.notebook.index(tab_id)

        # Work out new tab index
        if traverse_next:
            if (index >= num_tabs - 1): index = 0
            else:                       index += 1
        else:
            if index == 0:              index = num_tabs - 1
            else:                       index -= 1

        # Select new tab
        self.notebook.select(index)

        # Set focus on the terminal
        new_tab_id = self.notebook.select()
        terminal = self.notebook.nametowidget(new_tab_id)
        terminal.TerminalScreen.focus_set()

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

    def _close_tab(self, index=None, event=None):
        """ Close tab event """

        try:

            if event:
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