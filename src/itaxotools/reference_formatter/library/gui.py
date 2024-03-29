#!/usr/bin/env python

import logging
from typing import Dict, Optional, Union, Callable
from tkinterweb import HtmlFrame
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfiledialog
import tkinter.messagebox as tkmessagebox
import tkinter.font as tkfont
from enum import IntEnum
import os
from pathlib import Path

from .citation import (
    process_reference_file,
    txt_first_step,
    txt_second_step,
    process_reference_html,
    StepOrderViolated,
)
from .options import (
    OptionGroup,
    Options,
    OptionsDict,
    options_on_by_default,
    primary_options,
)
from .journal_list import JournalMatcher
from .resources import get_resource
from . import crossref


class TkWarnLogger(logging.Handler):
    """Displays warnings with TK messagebox"""

    def __init__(self, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.addFilter(lambda record: record.levelno == logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        tkmessagebox.showwarning("Warning", record.getMessage())
        print(record.pathname, record.lineno, sep=": ")
        print("Warning:", record.getMessage(), "\n")


class TkErrorLogger(logging.Handler):
    """Displays errors with TK messagebox"""

    def __init__(self, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.addFilter(lambda record: record.levelno == logging.ERROR)

    def emit(self, record: logging.LogRecord) -> None:
        tkmessagebox.showerror("Error", record.getMessage())
        print(record.pathname, record.lineno, sep=": ")
        print("Error:", record.getMessage(), "\n")


class FmtParameters(ttk.LabelFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_options: Dict[Options, Union[tk.Variable, ttk.Combobox]] = {}
        self.group_frames: Dict[OptionGroup, ttk.LabelFrame] = {
            group: ttk.LabelFrame(self, text=str(group), relief="sunken")
            for group in list(OptionGroup)
        }
        for option in list(Options):
            group_frame = self.group_frames[option.option_group()]
            if option.type is bool:
                var = tk.BooleanVar(self, value=option in options_on_by_default)
                self.get_options[option] = var
                check = ttk.Checkbutton(
                    group_frame, text=option.description, variable=var
                )
                if option in primary_options:
                    group_frame.configure(labelwidget=check)
                else:
                    check.pack(side=tk.TOP, fill=tk.X)
            elif issubclass(option.type, IntEnum):
                option_frame = ttk.Frame(group_frame)
                ttk.Label(option_frame, text=option.description).pack(side=tk.LEFT)
                cmbox = ttk.Combobox(
                    option_frame,
                    state="readonly",
                    values=list(map(str, list(option.type))),
                )
                cmbox.current(0)
                cmbox.pack(side=tk.LEFT, fill=tk.X)
                self.get_options[option] = cmbox
                option_frame.pack(side=tk.TOP, fill=tk.X)
            for _, group_frame in self.group_frames.items():
                group_frame.pack(side=tk.TOP, fill=tk.X)

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
        self.create_banner()
        self.create_top_frame()
        self.parameters_frame = FmtParameters(self, text="Parameters")
        self.create_preview_frame()

        self.banner.grid(row=0, column=0, sticky="nwse", columnspan=2)
        self.top_frame.grid(row=1, column=0, sticky="nwse", columnspan=2)

        ttk.Label(self, text="Input file").grid(
            row=2, column=0, sticky="w", columnspan=2
        )

        self.input_file = tk.StringVar()
        ttk.Entry(self, textvariable=self.input_file).grid(
            row=3, column=0, sticky="we", columnspan=2
        )

        self.parameters_frame.grid(row=4, column=0, sticky="nsew")
        self.preview_frame.grid(row=4, column=1, sticky="nsew")

        self.rowconfigure(4, weight=1)
        self.columnconfigure(1, weight=1)

        self.grid(sticky="nsew")
        logger = logging.getLogger()
        logger.addHandler(TkWarnLogger())
        logger.addHandler(TkErrorLogger())
        logger.setLevel(logging.WARNING)

    def create_banner(self) -> None:
        self.banner = ttk.Frame(self)
        ttk.Separator(self.banner, orient="horizontal").pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(
            self.banner, text="reference_formatter", font=tkfont.Font(size=20)
        ).pack(side=tk.LEFT)

        self.logo = tk.PhotoImage(
            file=get_resource("iTaxoTools Digital linneaeus MICROLOGO.png")
        )

        ttk.Label(self.banner, image=self.logo).pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Separator(self.banner, orient="vertical").pack(side=tk.RIGHT, fill=tk.Y)

    def create_top_frame(self) -> None:
        self.top_frame = ttk.Frame(self)
        self.top_frame.rowconfigure(0, weight=1)
        self.top_frame.columnconfigure(6, weight=1)

        ttk.Button(self.top_frame, text="Open", command=self.open_command).grid(
            row=0, column=0
        )
        ttk.Button(self.top_frame, text="Save", command=self.save_command).grid(
            row=0, column=1
        )
        ttk_style = ttk.Style()
        ttk_style.configure("Run.TButton", background="blue")
        ttk.Button(
            self.top_frame,
            text="Run",
            command=self.run_command(interactive=False),
            style="Run.TButton",
        ).grid(row=0, column=2)
        ttk.Button(
            self.top_frame,
            text="Run step 1",
            command=self.run_command(interactive=True),
        ).grid(row=0, column=3)
        ttk.Button(
            self.top_frame, text="Run step 2", command=self.run_second_step
        ).grid(row=0, column=4)
        ttk.Button(self.top_frame, text="Clear", command=self.clear_command).grid(
            row=0, column=5
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
        self.html_preview.load_url(
            Path(preview_file_path).resolve().as_uri(), force=True
        )

    def switch_preview(self) -> None:
        if self.make_rendered.get():
            self.plain_preview.grid_remove()
            self.html_preview.grid()
        else:
            self.html_preview.grid_remove()
            self.plain_preview.grid()

    def run_command(self, interactive: bool) -> Callable[[], None]:
        def run() -> None:
            self.clear_command()
            options = self.parameters_frame.get()
            if options[Options.ProcessJournalName] and not self.journal_matcher:
                msg = tk.Toplevel(self)
                if self.tk.call("tk", "windowingsystem") == "x11":
                    msg.attributes("-type", "splash")
                msg.title("Please wait")
                ttk.Label(msg, text="Loading journals' names").grid()
                self.update()
                self.journal_matcher = JournalMatcher()
                msg.destroy()
                self.update()
            if options[Options.CrossrefAPI] and not crossref.ETIQUETTE_EMAIL:
                logging.warning(
                    "CrossRef API asks polite users to provide their email.\n"
                    "\n"
                    "Please put a valid email into "
                    f"{get_resource('crossref_etiquette_email.txt')}"
                )
            try:
                with open(self.input_file.get(), errors="replace") as infile:
                    if options[Options.HtmlFormat]:
                        if not interactive:
                            process_reference_html(
                                infile, self.preview_dir, options, self.journal_matcher
                            )
                        else:
                            logging.warning(
                                "Two step transformation is"
                                "not yet supported for HTML format"
                            )
                    else:
                        if self.input_has_html_extension():
                            logging.warning(
                                "Input might be html file."
                                ' Consider enabling "HTML format" option.'
                            )
                        if interactive:
                            txt_first_step(
                                infile, self.preview_dir, options, self.journal_matcher
                            )
                        else:
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

        return run

    def run_second_step(self) -> None:
        self.clear_command()
        second_input = Path(self.preview_dir) / "input2"
        second_input.unlink(missing_ok=True)
        (Path(self.preview_dir) / "output").rename(second_input)
        with open(second_input) as input2:
            try:
                txt_second_step(
                    input2,
                    self.preview_dir,
                    self.parameters_frame.get(),
                    self.journal_matcher,
                )
            except StepOrderViolated:
                logging.error(
                    "Something went wrong.\n"
                    "Perhaps you didn't run step 1 before step 2"
                )
                return
            self.make_preview()

    def input_has_html_extension(self) -> bool:
        _, ext = os.path.splitext(self.input_file.get())
        return ext.startswith(".htm")

    def create_preview_frame(self) -> None:
        self.preview_frame = ttk.LabelFrame(self, text="Preview")
        self.preview_frame.rowconfigure(1, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)

        self.make_rendered = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.preview_frame,
            text="Preview rendered",
            variable=self.make_rendered,
            command=self.switch_preview,
        ).grid(row=0, column=0, sticky="w")

        self.plain_preview = ttk.Frame(self.preview_frame)
        self.plain_preview.rowconfigure(0, weight=1)
        self.plain_preview.columnconfigure(0, weight=1)
        self.plain_preview.grid(row=1, column=0, sticky="nsew")

        self.preview = tk.Text(self.plain_preview, height=15, width=30, wrap="none")
        self.preview.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(
            self.plain_preview, orient="vertical", command=self.preview.yview
        )
        self.preview.config(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="nsew")

        xscroll = ttk.Scrollbar(
            self.plain_preview, orient="horizontal", command=self.preview.xview
        )
        self.preview.config(xscrollcommand=xscroll.set)
        xscroll.grid(row=1, column=0, sticky="nsew")

        self.html_preview = HtmlFrame(self.preview_frame)
        self.html_preview.enable_caches(False)
        self.html_preview.grid(row=1, column=0, sticky="nsew")
        self.html_preview.grid_remove()
