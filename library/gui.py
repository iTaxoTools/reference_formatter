#!/usr/bin/env python

from typing import Dict, Optional, Union
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog
import tkinter.messagebox as tkmessagebox
from enum import IntEnum
import os

from library.citation import (
    Options,
    OptionsDict,
    process_reference_file,
    process_reference_html,
    options_on_by_default,
)
from library.journal_list import JournalMatcher


class FmtParameters(ttk.LabelFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_options: Dict[Options, Union[tk.Variable, ttk.Combobox]] = {}
        row = 0
        for option in list(Options):
            if option.type is bool:
                var = tk.BooleanVar(self, value=option in options_on_by_default)
                self.get_options[option] = var
                ttk.Checkbutton(self, text=option.description, variable=var).grid(
                    row=row, column=0, sticky="w", columnspan=2
                )
            elif issubclass(option.type, IntEnum):
                ttk.Label(self, text=option.description).grid(
                    row=row, column=0, sticky="w"
                )
                cmbox = ttk.Combobox(
                    self, state="readonly", values=list(map(str, list(option.type)))
                )
                cmbox.current(0)
                cmbox.grid(row=row, column=1, sticky="w")
                self.get_options[option] = cmbox
            row += 1
        self.rowconfigure(row, weight=1)
        self.columnconfigure(1, weight=1)

    def get(self) -> OptionsDict:
        result: OptionsDict = {}
        for option, var_or_cmb in self.get_options.items():
            if isinstance(var_or_cmb, tk.Variable):
                result[option] = var_or_cmb.get()
            elif isinstance(var_or_cmb, ttk.Combobox):
                result[option] = option.type(var_or_cmb.current())
        return result


class FmtGui(ttk.Frame):
    def __init__(self, *args, **kwargs):
        self.preview_dir = kwargs.pop("preview_dir")
        self.journal_matcher: Optional[JournalMatcher] = None
        super().__init__(*args, **kwargs)
        self.create_top_frame()
        self.parameters_frame = FmtParameters(self, text="Parameters")
        self.create_preview_frame()

        self.top_frame.grid(row=0, column=0, sticky="nwse", columnspan=2)

        ttk.Label(self, text="Input file").grid(
            row=1, column=0, sticky="w", columnspan=2
        )

        self.input_file = tk.StringVar()
        ttk.Entry(self, textvariable=self.input_file).grid(
            row=2, column=0, sticky="we", columnspan=2
        )

        self.parameters_frame.grid(row=3, column=0, sticky="nsew")
        self.preview_frame.grid(row=3, column=1, sticky="nsew")

        self.rowconfigure(3, weight=1)
        self.columnconfigure(1, weight=1)

        self.grid(sticky="nsew")

    def create_top_frame(self) -> None:
        self.top_frame = ttk.Frame(self)
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.columnconfigure(3, weight=1)

        ttk.Button(self.top_frame, text="Open", command=self.open_command).grid(
            row=0, column=0
        )
        ttk.Button(self.top_frame, text="Save", command=self.save_command).grid(
            row=0, column=1
        )
        ttk.Button(self.top_frame, text="Run", command=self.run_command).grid(
            row=0, column=2
        )

    def clear_command(self) -> None:
        self.preview.delete("1.0", "end")

    def open_command(self) -> None:
        input_path = tkfiledialog.askopenfilename()
        if input_path:
            self.input_file.set(os.path.abspath(input_path))

    def save_command(self) -> None:
        output_path = tkfiledialog.asksaveasfilename()
        if output_path:
            with open(output_path, mode="w") as outfile:
                outfile.write(self.preview.get("1.0", "end"))

    def make_preview(self) -> None:
        preview_file_path = os.path.join(self.preview_dir, "output")
        with open(preview_file_path) as preview_file:
            self.preview.insert("1.0", preview_file.read())

    def run_command(self) -> None:
        self.clear_command()
        options = self.parameters_frame.get()
        if options[Options.ProcessJournalName] and not self.journal_matcher:
            msg = tk.Toplevel(self)
            if self.tk.call('tk', 'windowingsystem') == 'x11':
                msg.attributes("-type", "splash")
            msg.title("Please wait")
            ttk.Label(msg, text="Loading journals' names").grid()
            self.update()
            self.journal_matcher = JournalMatcher()
            msg.destroy()
            self.update()
        try:
            with open(self.input_file.get(), errors="replace") as infile:
                if options[Options.HtmlFormat]:
                    process_reference_html(
                        infile, self.preview_dir, options, self.journal_matcher)
                else:
                    if self.input_has_html_extension():
                        tkmessagebox.showwarning(
                            "Warning", "Input might be html file."
                            " Consider enabling \"HTML format\" option.")
                    process_reference_file(
                        infile, self.preview_dir, options, self.journal_matcher
                    )
        except FileNotFoundError:
            tkmessagebox.showerror(
                "Error", f"File {self.input_file.get()} cannot be opened"
            )
        else:
            self.make_preview()
            tkmessagebox.showinfo("Done", "Processing is complete")

    def input_has_html_extension(self) -> bool:
        _, ext = os.path.splitext(self.input_file.get())
        return ext.startswith(".htm")

    def create_preview_frame(self) -> None:
        self.preview_frame = ttk.LabelFrame(self, text="Preview")
        self.preview_frame.rowconfigure(0, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)

        self.preview = tk.Text(self.preview_frame, height=15, width=30, wrap="none")
        self.preview.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(
            self.preview_frame, orient="vertical", command=self.preview.yview
        )
        self.preview.config(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="nsew")

        xscroll = ttk.Scrollbar(
            self.preview_frame, orient="horizontal", command=self.preview.xview
        )
        self.preview.config(xscrollcommand=xscroll.set)
        xscroll.grid(row=1, column=0, sticky="nsew")
