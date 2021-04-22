#!/usr/bin/env python

import tkinter as tk
import tempfile
import os

from library.gui import FmtGui


def gui_main():
    root = tk.Tk()

    root.title("Reference-formatter")
    preview_dir = tempfile.mkdtemp()

    def close_window():
        for file in os.scandir(preview_dir):
            os.remove(file)
        os.rmdir(preview_dir)
        root.destroy()
        root.quit()

    root.protocol("WM_DELETE_WINDOW", close_window)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    FmtGui(root, preview_dir=preview_dir)

    root.mainloop()


if __name__ == "__main__":
    gui_main()
