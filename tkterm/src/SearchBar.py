import tkinter as tk
from tkinter import *
from tkinter import ttk

from .Tooltip import Tooltip
from .Utils import get_absolute_path

class SearchBar():

    def __init__(self, parent):
        self.TerminalScreen = parent.TerminalScreen
        self.frameTerminal = parent.frameTerminal
        self._init()

    def _init(self):

        ## Bind keys
        self.TerminalScreen.bind('<Control-f>', self.open_searchbar)
        self.TerminalScreen.bind('<Escape>', self.close_searchbar)

        self.foundList = []
        self._reset()

        self.click_close    = PhotoImage(file=get_absolute_path(__file__, "../img", 'close.png'))
        self.click_next     = PhotoImage(file=get_absolute_path(__file__, "../img", 'next.png'))
        self.click_prev     = PhotoImage(file=get_absolute_path(__file__, "../img", 'prev.png'))
        self.click_regex    = PhotoImage(file=get_absolute_path(__file__, "../img", 'regex.png'))
        self.click_case     = PhotoImage(file=get_absolute_path(__file__, "../img", 'case.png'))


    def _reset(self):
        """ Reset attributes """

        self.searchIsOpen = False
        self.searchCaseSensitive = False
        self.searchRegex = False

        self.foundList.clear()
        self.currentSearchIndex = 0
        self.searchFoundCount = 0
        self.frameSearchBar = None
        self.searchRegexTooltip = None

    def open_searchbar(self, event):

        self.search_config = {
            "bd"        : 0,
            "fg"        : "white",
            "bg"        : "#21252B",
            "relief"    : FLAT,
            "font"      : ("Helvetica", 8)
        }

        if not self.searchIsOpen:

            ## Create searchbar frame
            self.frameSearchBar = tk.Frame(self.frameTerminal, width=20, height=50, borderwidth=0, bg="#21252B", relief=FLAT)

            self.searchFieldText = StringVar()

            self.searchField = Entry(
                self.frameSearchBar,
                textvariable = self.searchFieldText,
                fg="#b2b2b3",
                bg="#1d1f23",
                insertbackground="white",
                relief=FLAT,
                highlightbackground="#1d1f23",
                font=("Helvetica", 8)
            )

            self.searchField.pack(side=LEFT, padx=(5,0), pady=(5))

            # Bind keys
            self.searchField.bind("<Return>",       lambda event: self.do_search_next_or_prev(isNext=True))
            self.searchField.bind("<Shift-Return>", lambda event: self.do_search_next_or_prev(isNext=False))
            self.searchField.bind('<Escape>',       self.close_searchbar)

            self.searchFieldText.trace("w", self.do_search)

            self.searchResultText = StringVar()
            self.searchResultText.set("No results")

            def toggle_searchRegex():
                self.searchRegex = not self.searchRegex

                bg = "red" if self.searchRegex else "#1d1f23"
                self.searchRegexButton.configure(bg=bg)

                self.do_search()

            def toggle_searchCaseSensitive():
                self.searchCaseSensitive = not self.searchCaseSensitive

                bg = "red" if self.searchCaseSensitive else "#1d1f23"
                self.searchCaseButton.configure(bg=bg)

                self.do_search()

            self.searchCaseButton = Button(self.frameSearchBar, cursor="hand2", image=self.click_case, bg="#1d1f23", relief=FLAT, bd=0, highlightbackground="#1d1f23", command=toggle_searchCaseSensitive)
            self.searchCaseButton.pack(side=LEFT, fill=Y, pady=5)
            Tooltip(self.searchCaseButton, text="Match Case", delay=1)

            self.searchRegexButton = Button(self.frameSearchBar, cursor="hand2", image=self.click_regex, bg="#1d1f23", relief=FLAT, bd=0, highlightbackground="#1d1f23", command=toggle_searchRegex)
            self.searchRegexButton.pack(side=LEFT, fill=Y, pady=5)
            Tooltip(self.searchRegexButton, text="Use Regular Expression", delay=1)

            self.searchResult   = Label(self.frameSearchBar, textvariable=self.searchResultText, width=8, anchor=W, **self.search_config)
            self.searchResult.pack(side=LEFT, padx=(5), fill=Y)

            self.searchPrev     = Button(self.frameSearchBar, cursor="hand2", image=self.click_prev, width=30, highlightbackground= "#21252B", command= lambda: self.do_search_next_or_prev(False), **self.search_config)
            self.searchPrev.pack(side=LEFT, padx=(2), fill=Y)
            Tooltip(self.searchPrev, text="Previous Match (Shift+Enter)", delay=1)

            self.searchNext     = Button(self.frameSearchBar, cursor="hand2", image=self.click_next, width=30, highlightbackground= "#21252B", command= lambda: self.do_search_next_or_prev(True), **self.search_config)
            self.searchNext.pack(side=LEFT, padx=(2), fill=Y)
            Tooltip(self.searchNext, text="Next Match (Enter)", delay=1)

            self.searchClose = Button(
                self.frameSearchBar,
                cursor="hand2",
                image=self.click_close,
                highlightbackground="#21252B",
                width=30,
                command=self.close_searchbar,
                **self.search_config
            )

            self.searchClose.pack(side=LEFT, padx=(2), fill=Y)

            ## Create extra binding event on top of what Tooltip had (add="+")
            self.searchPrev.bind("<Enter>", self.on_enter, add="+")
            self.searchPrev.bind("<Leave>", self.on_leave, add="+")

            self.searchNext.bind("<Enter>", self.on_enter, add="+")
            self.searchNext.bind("<Leave>", self.on_leave, add="+")

            self.searchClose.bind("<Enter>", self.on_enter, add="+")
            self.searchClose.bind("<Leave>", self.on_leave, add="+")

            self.frameSearchBar.place(rely=0, relx=1.0, x=-14, y=14, anchor="e")
            self.searchField.focus_set()
            self.searchIsOpen = True

        ## Destroy searchbar frame
        else:
            self.close_searchbar()

    def on_enter(self, e):
        e.widget["bg"] = "black"

        # Set activebackground
        e.widget["activebackground"] = "black"

    def on_leave(self, e):
        e.widget["bg"] = self.search_config["bg"]

    def close_searchbar(self, *args):

        if self.frameSearchBar:

            for child in self.frameSearchBar.winfo_children():
                child.destroy()

            self.frameSearchBar.destroy()

            self._reset()

            self.TerminalScreen.tag_remove("found", "1.0", END)
            self.TerminalScreen.tag_remove("found_selected", "1.0", END)

            self.TerminalScreen.focus_set()

        self.frameSearchBar = None

    def do_search(self, *args):

        value = self.searchFieldText.get()

        self.TerminalScreen.tag_remove("found", "1.0", END)
        self.TerminalScreen.tag_remove("found_selected", "1.0", END)
        self.searchResultText.set("No results")

        self.foundList.clear()

        if not self.searchRegexTooltip:
            self.searchRegexTooltip = Tooltip(self.searchField, "", manual=True)
        else:
            self.searchRegexTooltip.close()

        self.searchField.configure(bg = "#1d1f23")

        if value:

            idx = "1.0"
            self.searchFoundCount = 0
            self.currentSearchIndex = 0

            while True:

                try:
                    idx = self.TerminalScreen.search(value, idx, nocase=(not self.searchCaseSensitive), stopindex=END, regexp=self.searchRegex)
                    self.searchField.configure(bg = "#1d1f23")
                except Exception as err:
                    # self.searchField.configure(borderwidth= 2)
                    self.searchField.configure(bg = "red")
                    self.searchRegexTooltip.text = err
                    self.searchRegexTooltip.create()
                    break

                if not idx:
                    self.searchResult['fg'] = "#f4875b" if self.searchFoundCount == 0 else "#b2b2b3"
                    break

                lastidx = "{}+{}c".format(idx, len(value))

                self.foundList.append((idx, lastidx))

                self.TerminalScreen.tag_add("found", idx, lastidx)
                idx = lastidx

                self.TerminalScreen.tag_config("found", background="green")
                self.searchFoundCount += 1


            if self.foundList:
                self.searchResultText.set("{} of {}".format(1, self.searchFoundCount))
                self.TerminalScreen.tag_add("found_selected", self.foundList[0][0], self.foundList[0][1])
                self.TerminalScreen.see(self.foundList[0][0])

            self.TerminalScreen.tag_config("found_selected", background="orange")

    def do_search_next_or_prev(self, isNext):

        self.TerminalScreen.tag_remove("found_selected", "1.0", END)

        if self.foundList:

            if isNext:
                self.currentSearchIndex = (self.currentSearchIndex + 1) % self.searchFoundCount
            else:
                self.currentSearchIndex = (self.currentSearchIndex - 1) % self.searchFoundCount

            self.searchResultText.set("{} of {}".format(self.currentSearchIndex + 1, self.searchFoundCount))
            self.TerminalScreen.tag_add("found_selected", self.foundList[self.currentSearchIndex][0], self.foundList[self.currentSearchIndex][1])


            self.TerminalScreen.see(self.foundList[self.currentSearchIndex][0])

