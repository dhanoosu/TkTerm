

def get_last_line(widget):
    """ Get the position of the last line from Text Widget"""

    pos = widget.index("end linestart")
    pos = float(pos) - 1
    return pos