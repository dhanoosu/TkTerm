import os

class TkTermConfig():

    # Default config
    DEFAULT_CONFIG = {
        "fg"                : "#00A79D",
        "bg"                : "#282C34",
        "insertbackground"  : "white",
        "error"             : "red",
        "output"            : "#E6E6E6",
        "basename"          : "#0080ff",
        "cursorshape"       : "bar",
        "selectbackground"  : "#464E5E",
        "fontfamily"        : "Cascadia Code SemiLight",
        "fontsize"          : 9
    }

    # Curernt config
    CONFIG = {}

    # Configuration filename
    CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../tkterm_settings.json"))

    @staticmethod
    def get_default(key=None):
        if key:
            assert(key in TkTermConfig.DEFAULT_CONFIG.keys())
            return TkTermConfig.DEFAULT_CONFIG[key]

        return TkTermConfig.DEFAULT_CONFIG.copy()

    @staticmethod
    def set_default(config):
        TkTermConfig.DEFAULT_CONFIG = config.copy()

    @staticmethod
    def get_config(key=None):
        if key:
            assert(key in TkTermConfig.CONFIG)
            return TkTermConfig.CONFIG[key]

        return TkTermConfig.CONFIG.copy()

    @staticmethod
    def set_config(config):
        TkTermConfig.CONFIG = config

    @staticmethod
    def set_config_key(key, value):
        assert(key in TkTermConfig.CONFIG.keys())
        TkTermConfig.CONFIG[key] = value

    @staticmethod
    def get_config_file():
        return TkTermConfig.CONFIG_FILE