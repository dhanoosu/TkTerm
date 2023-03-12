from .InterpreterInterface import InterpreterInterface

import os
import sys
import subprocess

class InterpreterShell(InterpreterInterface):

    def __init__(self, interpreter_path=None):
        super().__init__()

        self.process_options = {
            "shell"                 : True,
            "stdout"                : subprocess.PIPE,
            "stderr"                : subprocess.PIPE,
            "universal_newlines"    : True,
            "cwd"                   : os.getcwd()
        }

        # Ignore utf-8 decode error which sometimes happens on early terminating
        if os.name != "nt":
            self.process_options["errors"] = "ignore"

        if interpreter_path:
            self.process_options['executable'] = interpreter_path

    def execute(self, command):
        return subprocess.Popen(command, **self.process_options)

    def terminate(self, processThread):

        if (os.name == 'nt'):
            process = subprocess.Popen(
                "TASKKILL /F /PID {} /T".format(processThread.pid),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            for line in process.stdout:
                print(line, end='')
            for line in process.stderr:
                print(line, file=sys.stderr, end='')

        else:
            os.system("pkill -TERM -P %s" % processThread.pid)

    def get_return_code(self, process):
        return process.poll()

    def get_prompt(self):
        return os.getcwd() + ">> "