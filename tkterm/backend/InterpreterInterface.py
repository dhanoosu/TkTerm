#
# Abstract Class of Command Interface
#
from abc import ABC, abstractmethod


class InterpreterInterface(ABC):

    def __init__(self, *kwargs):
        # super().__init__()

        self.stdout = None
        self.stderr = None
        self.exit_code = None

    @abstractmethod
    def execute(self, command):
        pass

    @abstractmethod
    def terminate(self, processThread):
        pass