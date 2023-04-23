import tkinter as tk
from tkinter import *
from tkinter import ttk

class Tooltip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info', manual=False, delay=False):
        self.widget = widget
        self.text = text
        self.delay = delay

        self.tw = None

        self.manual = manual

        if not manual:
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.close)

    def enter(self, event=None):
        # if self.delay:
        #     self.widget.winfo_toplevel().after(600, self.create)
        # else:
        #     self.create()
        # else:
        #     self.close()

        self.create()

    def create(self):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")

        if self.manual:
            x += self.widget.winfo_rootx() - 1
            y += self.widget.winfo_rooty() + 20
        else:
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 30

        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       relief='solid', borderwidth=1, wraplength=150,
                       font=("Helvetica", "7", "normal"))

        label.pack(ipadx=1)

    def close(self, *args):

        if self.tw:
            self.tw.destroy()
            self.tw = None
