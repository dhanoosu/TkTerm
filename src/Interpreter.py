import os
import sys

from tkinter import *
from tkinter import PhotoImage

sys.path.append("..")
from .Utils import *
from backend.InterpreterShell import InterpreterShell

class Interpreter():

    MAPPINGS = {
        "sh"        : "/bin/sh",
        "bash"      : "/bin/bash",
        "windows"   : None
    }

    BACKENDS = {}

    _ICONS = {}

    DEFAULT_SHELL = ""

    @staticmethod
    def add_interpreter(name, backend, icon=None, set_default=False):
        """ Add new interpreter """

        assert(not name in Interpreter.MAPPINGS.keys())
        assert(not name in Interpreter.BACKENDS.keys())

        Interpreter.MAPPINGS[name] = None
        Interpreter.BACKENDS[name] = backend

        if set_default:
            Interpreter.DEFAULT_SHELL = name

        Interpreter._ICONS[name] = icon

    @staticmethod
    def init_backends():
        """ Initialise interpreter backends """

        Interpreter.BACKENDS.clear()

        for name, path in Interpreter.MAPPINGS.items():
            Interpreter.BACKENDS[name] = InterpreterShell(path)

        # Set default interpreter based on operating system
        if (os.name == 'nt'):
            Interpreter.DEFAULT_SHELL = "windows"
        else:
           Interpreter.DEFAULT_SHELL = "bash"

        Interpreter._ICONS.clear()

        Interpreter._ICONS["sh"]        = PhotoImage(file=get_absolute_path(__file__, "../img", "linux.png"))
        Interpreter._ICONS["bash"]      = PhotoImage(file=get_absolute_path(__file__, "../img", "linux.png"))
        Interpreter._ICONS["windows"]   = PhotoImage(file=get_absolute_path(__file__, "../img", "windows.png"))

    @staticmethod
    def get_backends():
        """ Return Interpreter backends """

        return Interpreter.BACKENDS

    @staticmethod
    def get_interpreter(name):
        """ Get interpreter instance by name """

        assert(name in Interpreter.BACKENDS.keys())
        return Interpreter.BACKENDS[name]

    @staticmethod
    def get_default_shell():
        """ Get default shell based on operating system """

        return Interpreter.DEFAULT_SHELL

    @staticmethod
    def get_icon(name):
        # assert (name in Interpreter._ICONS.keys())

        if name in Interpreter._ICONS.keys():
            return Interpreter._ICONS[name]
        else:
            return Interpreter._ICONS["bash"]