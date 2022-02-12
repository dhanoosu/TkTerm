import tkinter as tk
from tkinter import *
from tkinter import ttk
import os

class CreateToolTip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info', manual=False):
        self.widget = widget
        self.text = text

        self.tw = None

        if not manual:
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.close)

    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() -1
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       relief='solid', borderwidth=1, wraplength=150,
                       font=("Helvetica", "7", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()

class SearchFunctionality:

    def Search_init(self):

        ## Bind to Ctrl-f
        self.TerminalScreen.bind('<Control-f>', self.searchbar_function)
        self.TerminalScreen.bind('<Escape>', self.close_search)

        self.foundList = []
        self.search_reset_attributes()

        self.click_close= PhotoImage(file=os.path.join("img", 'close.png'))
        self.click_next= PhotoImage(file=os.path.join("img", 'next.png'))
        self.click_prev= PhotoImage(file=os.path.join("img", 'prev.png'))
        self.click_regex= PhotoImage(file=os.path.join("img", 'regex.png'))
        self.click_case= PhotoImage(file=os.path.join("img", 'case.png'))


    def search_reset_attributes(self):
        self.searchIsOpen = False
        self.searchCaseSensitive = False
        self.searchRegex = False

        self.foundList.clear()
        self.currentSearchIndex = 0
        self.searchFoundCount = 0
        self.frameSearchBar = None
        self.searchRegexTooltip = None

    def searchbar_function(self, event):

        search_config = {
            "cursor"    : "arrow",
            "bd"        : 0,
            "fg"        : "white",
            "bg"        : "#21252B",
            "relief"    : FLAT,
            "font"      : ("Helvetica", 8)
        }

        ## Create searchbar frame
        if not self.searchIsOpen:
            # create an info window in the bottom right corner and
            # inset a couple of pixels
            self.frameSearchBar = tk.Frame(self.TerminalScreen, width=20, height=50, borderwidth=0, bg="#21252B", relief=FLAT)

            self.searchFieldText = StringVar()

            self.searchField = Entry(
                self.frameSearchBar,
                textvariable = self.searchFieldText,
                fg="white",
                bg="black",
                insertbackground="white",
                relief=FLAT,
                highlightbackground="black",
                font=("Helvetica", 8)
            )
            self.searchField.bind("<Return>",       lambda event: self.do_search_next_or_prev(isNext=True))
            self.searchField.bind("<Shift-Return>", lambda event: self.do_search_next_or_prev(isNext=False))
            self.searchField.bind('<Escape>',       self.close_search)


            self.searchFieldText.trace_add("write", self.do_search)


            self.searchField.pack(side=LEFT, padx=(5,0), pady=(5))


            self.searchResultText = StringVar()
            self.searchResultText.set("No results")

            def toggle_searchRegex():
                self.searchRegex = not self.searchRegex

                bg = "red" if self.searchRegex else "black"
                self.searchRegexButton.configure(bg=bg)

                self.do_search()

            def toggle_searchCaseSensitive():
                self.searchCaseSensitive = not self.searchCaseSensitive

                bg = "red" if self.searchCaseSensitive else "black"
                self.searchCaseButton.configure(bg=bg)

                self.do_search()

            self.searchCaseButton = Button(self.frameSearchBar, cursor="arrow", image=self.click_case, bg="black", relief=FLAT, bd=0, highlightbackground="black", command=toggle_searchCaseSensitive)
            self.searchCaseButton.pack(side=LEFT, fill=Y, pady=5)

            self.searchRegexButton = Button(self.frameSearchBar, cursor="arrow", image=self.click_regex, bg="black", relief=FLAT, bd=0, highlightbackground="black", command=toggle_searchRegex)
            self.searchRegexButton.pack(side=LEFT, fill=Y, pady=5)

            self.searchResult   = Label(self.frameSearchBar, textvariable=self.searchResultText, width=8, anchor=W, **search_config)
            self.searchResult.pack(side=LEFT, padx=(5), fill=Y)

            self.searchPrev     = Button(self.frameSearchBar, image=self.click_prev, width=30, highlightbackground= "#21252B", **search_config, command= lambda: self.do_search_next_or_prev(False))
            self.searchPrev.pack(side=LEFT, padx=(2), fill=Y)

            self.searchNext     = Button(self.frameSearchBar, image=self.click_next, width=30, highlightbackground= "#21252B", **search_config, command= lambda: self.do_search_next_or_prev(True))
            self.searchNext.pack(side=LEFT, padx=(2), fill=Y)

            self.searchClose = Button(
                self.frameSearchBar,
                # text="X",
                image=self.click_close,
                **search_config,
                highlightbackground="#21252B",
                width=30,
                command=self.close_search,
            )
            self.searchClose.pack(side=LEFT, padx=(2), fill=Y)

            self.frameSearchBar.place(rely=0, relx=1.0, x=2, y=14, anchor="e")
            self.searchField.focus_set()
            self.searchIsOpen = True

        ## Destroy searchbar frame
        else:
            self.close_search()

    def close_search(self, *args):

        if self.frameSearchBar:

            for child in self.frameSearchBar.winfo_children():
                child.destroy()

            self.frameSearchBar.destroy()

            self.search_reset_attributes()

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
            self.searchRegexTooltip = CreateToolTip(self.searchField, "", manual=True)
        else:
            self.searchRegexTooltip.close()

        self.searchField.configure(bg = "black")

        if value:

            idx = "1.0"
            self.searchFoundCount = 0
            self.currentSearchIndex = 0

            while True:

                try:
                    idx = self.TerminalScreen.search(value, idx, nocase=(not self.searchCaseSensitive), stopindex=END, regexp=self.searchRegex)
                    self.searchField.configure(bg = "black")
                except Exception as e:
                    # self.searchField.configure(borderwidth= 2)
                    self.searchField.configure(bg = "red")
                    self.searchRegexTooltip.text = e
                    self.searchRegexTooltip.enter()
                    break

                if not idx:
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

