[![PyPI](https://img.shields.io/pypi/v/tkterm)](https://pypi.org/project/tkterm)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tkterm)
![Platform](https://img.shields.io/powershellgallery/p/Pester?color=blue)

# TkTerm - Tkinter Terminal Emulator
A fully functional terminal emulator built on Tkinter library - perform all basic commands of a terminal

<p align="center">
<img src="https://raw.githubusercontent.com/dhanoosu/TkTerm/master/tkterm/img/snapshot2.png">
</p>

Under the hood it executes commands using Python's *subprocess* module and spawn as a thread. Pressing `Ctrl-C` will terminate current running command. Supports Unix shells (`sh` and `bash`) and Window's Command Prompt (`cmd.exe`) commands.

## Features
- Compatible with Windows and Unix systems
- Tabbed Terminal - `click & drag` to reorder, `middle-click` to close tab, `double-click` to rename
- Return Code (RC) of previous run commands is shown at the bottom status bar
- Settings to customise colours, font and cursor shape
- **Ctrl-C** to kill current running process
- **Ctrl-F** to search; supports case sensitivity and regex searches
- **UP** and **DOWN** arrow keys to cycle between next and previous commands in history
- Unix-like **tab completion** on files and directories
- Handles **multiline commands** using caret character `^` or `\`

## Requirements
The Tkinter GUI library is built into Python, so no 3rd party library is required.

Requires at least Python version 3.x and above.

## Installation
Get it from Github or PIP package manager

```bash
# From github
git clone https://github.com/dhanoosu/TkTerm.git

# From package manager
pip install tkterm
```

## Standalone usage
Navigate to downloaded folder and run script with

```bash
cd TkTerm

# Either of these will work
python tkterm
python tkterm/tkterm.py
```

If package was installed via pip

```bash
python -m tkterm
```

## Integration with other Tkinter application
The Terminal is implemented as a `Frame` widget and can easily be integrated to other Tkinter application by

```python
import tkinter as tk
from tkinter import *
from tkterm import Terminal

root = tk.Tk()

terminal = Terminal(root)
terminal.pack(fill=BOTH, expand=True)

root.mainloop()
```

> If downloaded via github append to system path before import
> ```python
> import sys
> sys.path.insert(0, "./TkTerm")
> from tkterm import Terminal
> ```

## Customisation options
Customise Terminal interface by `Right-click > Settings...`

<p align="center">
<img src="https://raw.githubusercontent.com/dhanoosu/TkTerm/master/tkterm/img/settings.png">
</p>

**Note**: \
Clicking `Save config` saves setting configuration to a file.\
Tkterm will automatically load this file the next time it starts up.

## Multiline command
Long lines of command can be broken up using a caret. A caret at the line end appends the next line command with the current command.
In Windows the caret is `^`, and UNIX is `\`.

For multiline command to be considered there must be ***no** trailing space after the caret*, for example:

- `$> ping ^` is considered
- `$> ping ^ ` is **not** considered

```bash
$>> echo I ^
> have apple ^
> and banana
I have apple and banana
```

## Author

Developed by Dhanoo Surasarang

Github: [@dhanoosu](https://github.com/dhanoosu)

## Links

- **GitHub:** https://github.com/dhanoosu/TkTerm
