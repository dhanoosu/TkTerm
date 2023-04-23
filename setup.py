from setuptools import setup, find_packages

def read_from_file(path):
    """Return content from file"""

    with open(path, "r") as f:
        text = f.read()

    return text

attrs = dict(
    name="tkterm",
    version="0.0.0b1",
    packages=find_packages(),
    include_package_data=True,
    long_description=read_from_file("README.md"),
    description="Terminal emulator built on Tkinter library.",
    long_description_content_type="text/markdown",
    author="Dhanoo Surasarang",
    author_email="dhanoo.surasarang@gmail.com",
    url="https://github.com/dhanoosu/tkterm",
    license="MIT",
    keywords=[
        "linux",
        "shell",
        "bash",
        "cli",
        "gui",
        "terminal",
        "command-line",
        "tkinter",
        "subprocess",
        "tkinter-graphic-interface",
        "terminal-emulator",
        "ttk",
        "commandprompt",
        "tkinter-gui",
        "tkinter-python",
        "tkinter-terminal",
        "tk-terminal",
        "tkinter-shell",
        "tkterminal"
    ],
    classifiers=[
        # "Development Status :: 5 - Production/Stable",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3"
    ],
    project_urls={
        "Documentation": "https://github.com/dhanoosu/TkTerm/blob/master/README.md",
        "Bug Tracker": "https://github.com/dhanoosu/tkterm/issues",
    },
    include_package_data_info=True,
)

setup(**attrs)