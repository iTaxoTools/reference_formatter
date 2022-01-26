#!/usr/bin/env python3

from typing import Dict, Optional

from .options import NameForm, OptionsDict, Options, Style, VolumeSeparator
from .handle_html import ExtractedTags


class Journal:
    def __init__(
        self,
        name: Dict[NameForm, str],
    ):
        self.name = name

    def format(self, options: OptionsDict, tags: ExtractedTags, span: slice) -> str:
        journal_name = self.name[options[Options.JournalNameForm]]
        if options[Options.HtmlFormat]:
            if options[Options.JournalStyle] == Style.Preserve:
                journal_name = tags.surround_tags(journal_name, span.start)
            else:
                journal_name = options[Options.JournalStyle].style(journal_name)
        return journal_name
