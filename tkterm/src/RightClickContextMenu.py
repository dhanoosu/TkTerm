import tkinter as tk
import tkinter.messagebox

from tkinter import *
from tkinter import ttk

from tkinter import colorchooser
from tkinter import font
from tkinter.font import Font

import json

from .Utils import *
from .Config import TkTermConfig


class RightClickContextMenu:

    def __init__(self, top_level, terminal):

        self.top = top_level
        self.terminal = terminal

        self.bind_menu()

        self.setting_win_top = False

    def bind_menu(self):
        self.menu = tk.Menu(self.terminal,
            tearoff=0,
            bg="#1D1F23",
            # bg="white",
            fg="white",
            # borderwidth=0,
            bd=1,
            relief=FLAT,
            activebackground="#2c313a",
            activeforeground="white",
            selectcolor="red",
            activeborderwidth=0,
        )

        self.menu.add_command(label ="Copy", accelerator=" "*10, command=self._copyClipboard)
        self.menu.add_command(label ="Paste", command=self._pasteClipboard)
        self.menu.add_command(label ="Reload", command=self._reloadScreen)
        self.menu.add_separator()
        self.menu.add_command(label="Settings...", command=self._showSettings)

        self.terminal.TerminalScreen.bind("<ButtonRelease-3>", self._popup)
        self.menu.bind('<FocusOut>', self.on_focusout_popup)

    def on_focusout_popup(self, event=None):
        self.menu.unpost()

    def _popup(self, event):

        try:
            # self.menu.tk_popup(event.x_root+1, event.y_root+1)
            self.menu.post(event.x_root+1, event.y_root+1)
            self.menu.focus_set()
        finally:
            self.menu.grab_release()

    def _copyClipboard(self):

        try:
            selected = self.terminal.TerminalScreen.selection_get()
        except Exception as e:
            selected = ""

        self.top.parent.clipboard_clear()
        self.top.parent.clipboard_append(selected)

    def _pasteClipboard(self):
        data = self.top.parent.clipboard_get()

        current_pos = self.terminal.TerminalScreen.index(INSERT)
        self.terminal.TerminalScreen.insert(current_pos, data)

    def _reloadScreen(self):
        self.terminal.clear_screen()

    def _showSettings(self):

        def _init():

            fieldTexts["background"].set(TkTermConfig.get_config("bg"))
            fieldTexts["foreground"].set(TkTermConfig.get_config("fg"))
            fieldTexts["basename"].set(TkTermConfig.get_config("basename"))
            fieldTexts["error"].set(TkTermConfig.get_config("error"))
            fieldTexts["output"].set(TkTermConfig.get_config("output"))
            fieldTexts["selectbackground"].set(TkTermConfig.get_config("selectbackground"))

            mappings = dict(zip(cursorShapeMappings.values(), cursorShapeMappings.keys()))
            cursorCombobox.set(mappings[TkTermConfig.get_config("cursorshape")])

            fontFamilyCombobox.set(TkTermConfig.get_config("fontfamily"))
            fontSizeFieldText.set(TkTermConfig.get_config("fontsize"))

        def _do_restoreDefault():

            # self.top.TerminalColors = self.top.DefaultTerminalColors.copy()
            TkTermConfig.set_config(TkTermConfig.get_default())
            _init()

        def _init_sample():

            sampleTerminal["state"] = "normal"

            try:

                isError = False

                sample_font = Font(family=fontFamilyCombobox.get(), size=int(fontSizeFieldText.get()))

                sampleTerminal["bg"] = fieldTexts["background"].get()
                sampleTerminal["selectbackground"] = fieldTexts["selectbackground"].get()
                sampleTerminal["font"] = sample_font

                sampleTerminal.delete("1.0", END)

                boldFont = Font(font=sample_font)
                boldFont.configure(weight="bold")

                sampleTerminal.insert(END, "basename>>")
                sampleTerminal.tag_add("basename", get_last_line(sampleTerminal), sampleTerminal.index("insert"))
                sampleTerminal.tag_config("basename", foreground=fieldTexts["basename"].get(), font=boldFont)

                sampleTerminal.insert(END, " ")

                start_pos = sampleTerminal.index("insert")

                sampleTerminal.insert(END, "command")
                sampleTerminal.tag_add("command", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("command", foreground=fieldTexts["foreground"].get())

                sampleTerminal.insert(END, "\n")

                start_pos = sampleTerminal.index("insert")

                output_text = """\
This is a sample output message from a given command
Second line ...
Third line ...
^C
"""
                sampleTerminal.insert(END, output_text)
                sampleTerminal.tag_add("output", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("output", foreground=fieldTexts["output"].get())


                start_pos = sampleTerminal.index("insert")

                error_text = "Terminate.\nAn error has occurred"
                sampleTerminal.insert(END, error_text)
                sampleTerminal.tag_add("error", start_pos, sampleTerminal.index("insert"))
                sampleTerminal.tag_config("error", foreground=fieldTexts["error"].get())

            except:
                isError = True

            sampleTerminal["state"] = "disabled"


        def _populate_color_fields(name, row, color="white"):

            label = tk.Label(frameSettings, text=name)

            field = StringVar()
            field.set(color)

            entry = tk.Entry(frameSettings, textvariable=field, relief=FLAT)
            button = tk.Button(frameSettings, width=2, height=1, relief=FLAT, cursor="hand2", command= lambda: _choose_color(field))

            field.trace("w", lambda *args: _update_color(button, field))

            label.grid(sticky="W", padx=(0,10), row=row, column=0)
            entry.grid(sticky="W", row=row, column=1)
            button.grid(sticky="W", padx=10, row=row, column=2)

            fieldTexts[name] = field

        def _update_color(entry, field):
            try:
                entry["text"] = ""
                entry["bg"] = field.get()
                entry["activebackground"] = field.get()
            except:
                entry["text"] = "Err"
                entry["bg"] = "white"
                entry["fg"] = "red"

            _init_sample()

        def _choose_color(field):

            try:
                result = colorchooser.askcolor(title="Color Chooser", parent=self.setting_win_top, initialcolor=field.get())
            except:
                result = colorchooser.askcolor(title="Color Chooser", parent=self.setting_win_top)

            field.set(result[1])

            _init_sample()

        def _do_ok():

            result = _do_apply()

            if result:
                self.setting_win_top.destroy()
            else:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()

        def _do_apply():

            try:
                TkTermConfig.CONFIG["bg"]               = fieldTexts["background"].get()
                TkTermConfig.CONFIG["fg"]               = fieldTexts["foreground"].get()
                TkTermConfig.CONFIG["cursorshape"]      = cursorShapeMappings[cursorCombobox.get()]
                TkTermConfig.CONFIG["fontfamily"]       = fontFamilyCombobox.get()
                TkTermConfig.CONFIG["fontsize"]         = fontSizeFieldText.get()
                TkTermConfig.CONFIG["output"]           = fieldTexts["output"].get()
                TkTermConfig.CONFIG["error"]            = fieldTexts["error"].get()
                TkTermConfig.CONFIG["basename"]         = fieldTexts["basename"].get()
                TkTermConfig.CONFIG["selectbackground"] = fieldTexts["selectbackground"].get()

                self.top.set_color_style()

            except:
                tkinter.messagebox.showerror(title="Invalid input", message="Found invalid input. Please check your settings")
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()
                return False

            return True

        def _update_cursorShapeSelected(*args):
            cursorCombobox.selection_clear()

            _init_sample()

        def _do_saveConfig():

            result = _do_apply()

            if result:
                with open(TkTermConfig.CONFIG_FILE, "w") as f:
                    f.write(json.dumps(TkTermConfig.get_config(), indent = 4))

                    tkinter.messagebox.showinfo(title="Configuration saved", message="Successfully saved configuration to file.\n{}".format(f.name))

            else:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()

        def _update_FontFamilySelected(*args):

            fontFamilyCombobox.selection_clear()
            _init_sample()

        def _change_font_size(mode):

            assert(mode in ["decrease", "increase"])

            if mode == "decrease":
                fontSizeFieldText.set(int(fontSizeFieldText.get()) - 1)
            elif mode == "increase":
                fontSizeFieldText.set(int(fontSizeFieldText.get()) + 1)

        #
        # If popup window existed, bring it up
        #
        if self.setting_win_top:
            try:
                self.setting_win_top.lift()
                self.setting_win_top.focus_set()
                return
            except:
                pass

        #
        # Create new popup window
        #
        self.setting_win_top = Toplevel(self.top.winfo_toplevel())
        self.setting_win_top.geometry("750x500")
        self.setting_win_top.resizable(False, False)

        self.setting_win_top.title("Settings")
        self.setting_win_top.focus_set()

        ########################################################################
        # Notebook
        ########################################################################

        tabControl = ttk.Notebook(self.setting_win_top)

        tab1 = tk.Frame(tabControl)
        tab1.pack(expand=True, fill=BOTH)

        ########################################################################
        # Tabs
        ########################################################################

        tabControl.pack(expand=True, fill=BOTH)
        tabControl.add(tab1, text ='Appearance')

        ########################################################################
        # Frames
        ########################################################################

        frameWrap = tk.Frame(tab1)
        frameWrap.pack(expand=True, fill=BOTH, padx=10, pady=10)

        frameTop = tk.Frame(frameWrap)
        frameTop.pack(expand=True, fill=X)

        frameSettings = tk.Frame(frameTop)
        frameSettings.pack(side=LEFT)

        frameSample = tk.Frame(frameTop, height=300, width=500)
        frameSample.pack_propagate(False)
        frameSample.pack(side=LEFT, padx=(10, 0))

        frameBottom = tk.Frame(tab1, relief=RAISED, bd=1, height=5)
        frameBottom.pack(side=BOTTOM, fill=X, ipadx=10, ipady=10)

        ########################################################################
        # Sample terminal
        ########################################################################

        sampleTerminal = tk.Text(frameSample)
        sampleTerminal.pack(expand=True, fill=BOTH)

        ########################################################################
        #
        ########################################################################

        fieldTexts = {}
        isError = False

        label_terminal = tk.Label(frameSettings, text="Terminal", font="Helvetica 16 bold")
        label_cursor = tk.Label(frameSettings, text="Cursor", font="Helvetica 16 bold")
        label_font = tk.Label(frameSettings, text="Font", font="Helvetica 16 bold")

        label_cusor_shape = tk.Label(frameSettings, text="Cursor shape")

        label_font_size = tk.Label(frameSettings, text="Font size")
        label_font_family = tk.Label(frameSettings, text="Font family")

        cursorShapeMappings = {
            "Bar ( | )" : "bar",
            "Block ( █ )" : "block"
        }


        fontSizeFieldText = IntVar()

        frameFontSize = tk.Frame(frameSettings)
        buttonFontSizeMinus = tk.Button(frameFontSize, text=" - ", relief=GROOVE, command= lambda:_change_font_size(mode="decrease")).pack(side=LEFT)
        entry_font_size = tk.Entry(frameFontSize, textvariable=fontSizeFieldText, relief=FLAT, justify=CENTER, width=5).pack(side=LEFT, ipady=3)
        buttonFontSizePlus = tk.Button(frameFontSize, text=" + ", relief=GROOVE, command= lambda:_change_font_size(mode="increase")).pack(side=LEFT)

        label_terminal.grid(sticky="W", ipady=10, row=2)

        _populate_color_fields(name="background", row=3)
        _populate_color_fields(name="foreground", row=4)
        _populate_color_fields(name="selectbackground", row=5)
        _populate_color_fields(name="basename", row=6)
        _populate_color_fields(name="output", row=7)
        _populate_color_fields(name="error", row=8)

        label_cursor.grid(sticky="W", ipady=10, row=9)
        label_cusor_shape.grid(sticky="W", row=10, column=0)

        cursorCombobox = ttk.Combobox(frameSettings, state="readonly", width=15, font=("Helvetica", 8))
        cursorCombobox['values'] = list(cursorShapeMappings.keys())
        cursorCombobox.bind("<<ComboboxSelected>>", _update_cursorShapeSelected)
        cursorCombobox.grid(sticky="W", ipady=3, row=10, column=1)

        label_font.grid(sticky="W", ipady=10, row=11)
        label_font_size.grid(sticky="W", row=12, column=0)
        frameFontSize.grid(sticky="W", row=12, column=1)

        label_font_family.grid(sticky="W", row=13, column=0)

        fontFamilyCombobox = ttk.Combobox(frameSettings, state="readonly", width=25)
        fontFamilyCombobox["values"] = list(font.families())
        fontFamilyCombobox.bind("<<ComboboxSelected>>", _update_FontFamilySelected)
        fontFamilyCombobox.grid(sticky="W", ipady=3, row=13, column=1)

        ttk.Button(frameBottom, style="Settings.TButton", text="Restore default", command=_do_restoreDefault).pack(side=LEFT, expand=True)

        ttk.Button(frameBottom, style="Settings.TButton", text="OK", command=_do_ok).pack(side=LEFT)
        ttk.Button(frameBottom, style="Settings.TButton", text="Apply", command=_do_apply).pack(side=LEFT)

        ttk.Button(frameBottom, style="Settings.TButton", text="Save config", command=_do_saveConfig).pack(side=LEFT, expand=True)

        s = ttk.Style()
        s.map('Settings.TButton',
            background=[('disabled','#d9d9d9'), ('active','#ececec')],
            foreground=[('disabled','#a3a3a3')])


        fontSizeFieldText.trace("w", lambda *args: _init_sample())


        _init()
        _init_sample()