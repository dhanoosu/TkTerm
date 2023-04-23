import os

def get_last_line(widget):
    """ Get the position of the last line from Text Widget"""

    pos = widget.index("end linestart")
    pos = float(pos) - 1
    return pos

def get_absolute_path(root, *args):
    """ Get absolute path given a root """

    return os.path.join(os.path.dirname(os.path.abspath(root)), *args)