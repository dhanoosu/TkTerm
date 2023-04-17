from .InterpreterInterface import InterpreterInterface

import os
import sys
import subprocess

class InterpreterShell(InterpreterInterface):

    def __init__(self, interpreter_path=None):
        super().__init__()

        self.history = []

        self.process_options = {
            "shell"                 : True,
            "stdout"                : subprocess.PIPE,
            "stderr"                : subprocess.PIPE,
            "universal_newlines"    : True
        }

        # Ignore utf-8 decode error which sometimes happens on early terminating
        if os.name != "nt":
            self.process_options["errors"] = "ignore"

        if interpreter_path:
            self.process_options['executable'] = interpreter_path

    def execute(self, command):
        return subprocess.Popen(command, cwd=os.getcwd(), **self.process_options)

    def terminate(self, processThread):

        stdout = ""
        stderr = ""

        if (os.name == 'nt'):
            process = subprocess.Popen(
                "TASKKILL /F /PID {} /T".format(processThread.pid),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            for line in process.stdout:
                stdout += line
            for line in process.stderr:
                stderr += line

        else:

            try:
                os.system("pkill -TERM -P %s" % processThread.pid)
                os.system("kill -2 {}".format(processThread.pid))
                os.system("kill -9 {}".format(processThread.pid))
            except:
                pass

        processThread.wait()

        return (stdout, stderr)

    def get_return_code(self, process):
        return process.poll()

    def get_prompt(self):
        return os.getcwd() + ">> "

    def get_history(self):
        return self.history

    def __repr__(self):
        return "<InterpreterShell object: {}>".format(self.process_options['executable'])