import tkinter as tk
from tkinter import *
from tkinter import ttk

import webbrowser

from src.Utils import *
from src.Config import TkTermConfig
from src.TerminalScreen import TerminalWidget
from src.SearchBar import SearchBar
from src.RightClickContextMenu import RightClickContextMenu

class TerminalTab(ttk.Notebook):

    def __init__(self, parent, splashText):

        ttk.Notebook.__init__(self, parent)

        self.parent = parent
        self.splashText = splashText

        ########################################################################
        # Bind keys
        ########################################################################
        self.bind("<B1-Motion>", self._reorder_tab)
        self.bind("<ButtonRelease-2>", lambda e: self._close_tab(event=e))
        self.bind("<<NotebookTabChanged>>", self._tab_clicked)
        self.bind('<Double-Button-1>', self._tab_rename)

        ########################################################################
        # Add default tabs
        # This will automatically create a tab and an add tab button
        ########################################################################
        self.iconPlus = PhotoImage(file=get_absolute_path(__file__, "../img", "plus.png"))
        self.add(tk.Frame(self.parent), image=self.iconPlus)

        # Set color profile for notebook
        self.init_style()

        ########################################################################
        # Create menu button
        ########################################################################
        self.frameNav = tk.Frame(self.parent)
        self.frameNav.place(rely=0, relx=1.0, x=-10, y=17, anchor="e")

        self.iconHamburger  = PhotoImage(file=get_absolute_path(__file__, "../img", "hamburger.png"))
        self.iconSearch     = PhotoImage(file=get_absolute_path(__file__, "../img", "search.png"))
        self.iconNewTab     = PhotoImage(file=get_absolute_path(__file__, "../img", "new_tab.png"))
        self.iconNextTab    = PhotoImage(file=get_absolute_path(__file__, "../img", "next_tab.png"))
        self.iconPrevTab    = PhotoImage(file=get_absolute_path(__file__, "../img", "prev_tab.png"))
        self.iconCloseTab   = PhotoImage(file=get_absolute_path(__file__, "../img", "close_tab.png"))

        self.renameCloseButton  = PhotoImage(file=get_absolute_path(__file__, "../img", "close.png"))
        self.iconApp            = PhotoImage(file=get_absolute_path(__file__, "../img", "app_icon.png"))

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

        self.configure(style="Terminal.TNotebook")

    def set_color_style(self):
        """ Set color style for all terminal tabs and notebook """

        for tab in self.tabs()[:-1]:
            terminal = self.nametowidget(tab)

            terminal.set_color_style()

        self.init_style()

    def _tab_menu_on_leave(self, event):
        """ Set effect when mouse cursor leave menu button """

        if event.widget["state"] == "normal":
            event.widget.config(bg="#414755")

    def _tab_menu(self, event):
        """ Create menu for menu button """

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
        for tab in self.tabs()[:-1]:

            self.tabListMenu.add_command(
                label="   " + self.tab(tab, option="text"),
                image=self.tab(tab, option="image"),
                compound=LEFT,
                command= lambda temp=tab: self.select(temp)
            )

        self.tabListMenu.add_separator()

        self.tabListMenu.add_command(
            label="   Search",
            accelerator="Ctrl+F",
            image=self.iconSearch, compound=LEFT,
            command=lambda : self.nametowidget(self.select()).event_generate("<Control-f>")
        )

        self.tabListMenu.add_command(
            label="   New tab",
            accelerator="Ctrl+T",
            command=self._insert_new_tab,
            image=self.iconNewTab, compound=LEFT
        )

        # Number of opened tabs (minus add tab button)
        num_tabs = len(self.tabs()) - 1

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
            command=lambda : self._close_tab(index=self.index(self.select())),
            state=state
        )

        self.tabListMenu.add_separator()

        self.tabListMenu.add_command(label="About TkTerm ...", command=self._about_page)

        self.tabListMenu.bind("<FocusOut>", lambda e: (
            e.widget.destroy(),
            event.widget.config(bg="#414755")
        ))

        ########################################################################
        # Create popup event
        ########################################################################

        try:
            event.widget.config(fg="#9da5b4", bg="#495162")
            self.tabListMenu.tk_popup(event.widget.winfo_rootx(), event.widget.winfo_rooty()+30)
            # self.tabListMenu.focus_set()
        finally:
            self.tabListMenu.grab_release()

            if os.name == "nt":
                event.widget.config(bg="#414755")

    def _tab_clicked(self, *event):
        """ Monitor tab change event """

        # Fake the last tab as insert new tab
        if self.select() == self.tabs()[-1]:
            self._insert_new_tab()

    def _insert_new_tab(self):
        """ Insert new tab event """

        terminal = TerminalWidget(self.parent)

        if self.splashText:
            terminal.update_shell(print_basename=False)
            terminal.stdout.write(self.splashText)

        terminal.update_shell()

        # Attach search bar to terminal
        terminal.searchBar = SearchBar(terminal)

        # Attach right click context menu
        terminal.contextMenu = RightClickContextMenu(self, terminal)

        # Insert new tab before the add button
        index = len(self.tabs()) - 1
        self.insert(index, terminal, text=f"Terminal {len(self.tabs())}", image=terminal.icon, compound=LEFT)
        self.select(index)

        # Bind event for each terminal instance
        tab_id = self.select()
        terminal.bind("<<eventUpdateShell>>",   lambda e : self._update_icon(tab_id))
        terminal.bind("<<eventNewTab>>",        lambda e : self._insert_new_tab())
        terminal.bind("<<eventCycleNextTab>>",  lambda e : self._cycle_through_tabs(traverse_next=True))
        terminal.bind("<<eventCyclePrevTab>>",  lambda e : self._cycle_through_tabs(traverse_next=False))

    def _cycle_through_tabs(self, traverse_next=True):
        """ Cycle through opened tabs """

        # Number of opened tabs (minus add tab button)
        num_tabs = len(self.tabs()) - 1

        # Get current tab id and its index
        tab_id = self.select()
        index = self.index(tab_id)

        # Work out new tab index
        if traverse_next:
            if (index >= num_tabs - 1): index = 0
            else:                       index += 1
        else:
            if index == 0:              index = num_tabs - 1
            else:                       index -= 1

        # Select new tab
        self.select(index)

        # Set focus on the terminal
        new_tab_id = self.select()
        terminal = self.nametowidget(new_tab_id)
        terminal.TerminalScreen.focus_set()

    def _update_icon(self, tab_id):
        """ Update icon on tab """

        terminal = self.nametowidget(tab_id)
        self.tab(tab_id, image=terminal.icon)

    def _reorder_tab(self, event):
        """ Drag to reorder tab """

        try:
            index = self.index(f"@{event.x},{event.y}")

            if index >= len(self.tabs()) - 1:
                return

            self.insert(index, child=self.select())

        except tk.TclError:
            pass

    def _close_tab(self, index=None, event=None):
        """ Close tab event """

        try:

            if event:
                index = self.index(f"@{event.x},{event.y}")

            # Do nothing if it is the last tab (add tab button)
            if index >= len(self.tabs()) - 1:
                return

            # Do nothing if there are 2 tabs left
            if len(self.tabs()) == 2:
                return

            # When closing the last tab, immediately switch to the tab before
            if index == len(self.tabs()) - 2:
                self.select(len(self.tabs()) - 3)

            terminal = self.nametowidget(self.tabs()[index])

            # TODO: Error on closing tabs if there are processes running
            # If process still running just kill it
            terminal.terminate()

            del terminal.searchBar
            del terminal.contextMenu

            for child in terminal.winfo_children():
                child.destroy()

            terminal.destroy()

            # self.event_generate("<<NotebookTabClosed>>")

        except Exception:
            pass

    def _tab_rename(self, event):
        """ Rename a tab """

        def _accept_change(event):
            """ Accept a change """

            self.tab(tab_id, text=field.get())
            _focus_out()

        def _focus_out(*event):
            """ On focus out destroy all created widgets """

            buttonClose.destroy()
            entry.destroy()
            frameInner.destroy()
            frame.destroy()

            terminal.TerminalScreen.focus_set()

        def _on_enter(event):
            event.widget["bg"] = INNER_BG
            event.widget["activebackground"] = INNER_BG

        def _on_leave(event):
            event.widget["bg"] = OUTER_BG

        try:

            # Define colors
            OUTER_BG = "#212224"
            INNER_BG = "#414755"

            # Get the selected tab
            index = self.index(f"@{event.x},{event.y}")
            self.select(index)
            tab_id = self.select()

            # Get the associated terminal widget
            terminal = self.nametowidget(tab_id)

            # Create a popup frame attached to terminal
            frame = tk.Frame(terminal, bg=OUTER_BG)
            frame.place(rely=0, x=event.x, y=13, anchor="w")

            frameInner = tk.Frame(frame, bg=OUTER_BG)
            frameInner.pack(expand=True, fill=BOTH, padx=5, pady=5)

            field = StringVar()

            entry = tk.Entry(
                frameInner,
                textvariable=field,
                bd=0,
                width=10,
                bg=INNER_BG,
                fg="white",
                insertbackground="white",
                borderwidth=0,
                font="Helvetica 9"
            )

            entry.pack(side=LEFT, expand=True, fill=BOTH)

            buttonClose = tk.Button(
                frameInner,
                image=self.renameCloseButton,
                bg=OUTER_BG,
                relief=FLAT,
                bd=0,
                height=15,
                highlightbackground=OUTER_BG,
                command=_focus_out
            )

            buttonClose.pack(side=LEFT, padx=(5, 0))

            # Get the tab label
            field.set(self.tab(tab_id, option="text"))

            # Set focus to Entry box and select all text by default
            entry.focus()
            entry.select_range(0, END)

            # Bind keys
            entry.bind("<Return>", _accept_change)
            entry.bind("<FocusOut>", _focus_out)
            entry.bind("<Escape>", _focus_out)

            buttonClose.bind("<Enter>", _on_enter)
            buttonClose.bind("<Leave>", _on_leave)

        except tk.TclError:
            pass

    def _about_page(self):
        """ About page """

        def _focus_out(*event):
            """ On focus out destroy all created widgets """

            background.destroy()
            button1.destroy()
            button2.destroy()
            frameButton.destroy()
            labelAbout.destroy()
            labelIcon.destroy()
            frameInner.destroy()
            frame.destroy()

            tab_id = self.select()
            terminal = self.nametowidget(tab_id)
            terminal.TerminalScreen.focus_set()

        # Define colors
        OUTER_BG = "#9da5b4"
        INNER_BG = "#414755"

        # Get screen dimension
        root_width = self.parent.winfo_width()
        root_height = self.parent.winfo_height()

        # Fill background to cover whole screen
        background = tk.Label(self.parent, bg=OUTER_BG, width=root_width, height=root_height)
        background.place(x=0, y=0)

        # Create a popup frame
        frame = tk.Frame(self.parent, bg=INNER_BG)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # Inner frame
        frameInner = tk.Frame(frame, bg=INNER_BG)
        frameInner.pack(expand=True, fill=BOTH, padx=20, pady=20)

        about_text = """
TkTerm - Terminal Emulator built on Tkinter library

Created by Dhanoo Surasarang
Github @dhanoosu

"""

        labelIcon = tk.Label(frameInner, image=self.iconApp, bg=INNER_BG)
        labelIcon.pack(side=TOP)

        labelAbout = tk.Label(frameInner, text=about_text, bg=INNER_BG, fg="white")
        labelAbout.pack(side=TOP)

        # Area for buttons
        frameButton = tk.Frame(frameInner, bg=INNER_BG)
        frameButton.pack(side=TOP)

        button1 = ttk.Button(frameButton, text="Visit github", takefocus=0, command=lambda : webbrowser.open("https://github.com/dhanoosu/TkTerm"))
        button1.pack(side=LEFT, expand=True, padx=5, ipadx=10)

        button2 = ttk.Button(frameButton, text="OK", takefocus=0, command=_focus_out)
        button2.pack(side=LEFT, expand=True, padx=5)

        # Bind keys
        frame.bind("<FocusOut>", _focus_out)
        background.bind("<ButtonRelease-1>", _focus_out)