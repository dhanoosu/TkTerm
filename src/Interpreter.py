import os
import sys
sys.path.append("..")
from backend.InterpreterShell import InterpreterShell

class Interpreter():

    MAPPINGS = {
        "sh"        : "/bin/sh",
        "bash"      : "/bin/bash",
        "windows"   : None
    }

    BACKENDS = {}

    DEFAULT_SHELL = ""

    @staticmethod
    def add_interpreter(name, backend, set_default=False):
        """ Add new interpreter """

        assert(not name in Interpreter.MAPPINGS.keys())
        assert(not name in Interpreter.BACKENDS.keys())

        Interpreter.MAPPINGS[name] = None
        Interpreter.BACKENDS[name] = backend

        if set_default:
            Interpreter.DEFAULT_SHELL = name

    @staticmethod
    def init_backends():
        """ Initialise interpreter backends """

        Interpreter.BACKENDS.clear()

        for name, path in Interpreter.MAPPINGS.items():
            Interpreter.BACKENDS[name] = InterpreterShell(path)

        if (os.name == 'nt'):
            Interpreter.DEFAULT_SHELL = "windows"
        else:
           Interpreter.DEFAULT_SHELL = "bash"

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