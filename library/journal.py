#!/usr/bin/env python3

from typing import Dict, Optional

from library.options import NameForm, OptionsDict, Options, Style, VolumeSeparator
from library.handle_html import ExtractedTags


class Journal:
    def __init__(
        self,
        name: Dict[NameForm, str],
        extra: Optional[str],
    ):
        self.name = name
        self.extra = extra

    def format(self, options: OptionsDict, tags: ExtractedTags, span: slice) -> str:
        journal_name = self.name[options[Options.JournalNameForm]]
        if options[Options.HtmlFormat]:
            if options[Options.JournalStyle] == Style.Preserve:
                journal_name = tags.surround_tags(journal_name, span.start)
            else:
                journal_name = options[Options.JournalStyle].style(journal_name)
        formatted_name = (
            options[Options.JournalSeparator].format()
            + " "
            + journal_name
            + (self.extra or "")
        )
        if (
            options[Options.VolumeSeparator] == VolumeSeparator.Period
            and formatted_name[-1] == "."
        ):
            formatted_name = formatted_name[:-1]

        return formatted_name + options[Options.VolumeSeparator].format()
