#!/usr/bin/env python

from typing import Dict, Callable, Any, Union
import tkinter as tk
import tkinter.ttk as ttk
from enum import IntEnum

from library.citation import Options, OptionsDict


class FmtParameters(tk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_options: Dict[Options, Union[tk.Variable, ttk.Combobox]] = {}
        row = 0
        for option in list(Options):
            if option.type is bool:
                self.get_options[option] = tk.BooleanVar(self, value=False)
                ttk.Checkbutton(self, text=option.description, variable=self.get_options[option]).grid(
                    row=row, column=0, sticky="w")
            elif issubclass(option.type, IntEnum):
                ttk.Label(self, text=option.description).grid(
                    row=row, column=0, sticky="w")
                cmbox = ttk.Combobox(self, state='readonly', values=list(
                    map(str, list(option.type))))
                cmbox.current(0)
                cmbox.grid(row=row, column=1, sticky="w")
                self.get_options[option] = cmbox
            row += 1

    def get(self) -> OptionsDict:
        result: OptionsDict = {}
        for option, var_or_cmb in self.get_options.items():
            if isinstance(var_or_cmb, tk.Variable):
                result[option] = var_or_cmb.get()
            elif isinstance(var_or_cmb, ttk.Combobox):
                result[option] = option.type(var_or_cmb.current())
        return result


class FmtGui(tk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
