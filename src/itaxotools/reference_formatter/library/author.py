#!/usr/bin/env python3

from typing import Optional

from .options import OptionsDict, Options, Style
from .handle_html import ExtractedTags


class Author:
    def __init__(
        self, span: slice, surname: Optional[str] = None, initials: Optional[str] = None
    ):
        if surname is None or initials is None:
            self.is_et_al = True
            return
        self.is_et_al = False
        self.surname = surname
        self.initials = initials.replace(" ", "")
        self.span = span

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Author):
            return NotImplemented
        if self.is_et_al and other.is_et_al:
            return True
        return (
            not self.is_et_al
            and not other.is_et_al
            and self.surname == other.surname
            and self.initials == other.initials
            and self.span == other.span
        )

    def format_author(self, options: OptionsDict, first: bool, tags: ExtractedTags):
        if self.is_et_al:
            if options[Options.InitialsNoPeriod]:
                return "et al"
            else:
                return "et al."
        if options[Options.InitialsNoPeriod]:
            initials = self.initials.replace(".", "")
        else:
            initials = self.initials
        if options[Options.HtmlFormat]:
            if options[Options.SurnameStyle] == Style.Preserve:
                surname = tags.surround_tags(self.surname, self.span.start)
            else:
                surname = options[Options.SurnameStyle].style(self.surname)
        else:
            surname = self.surname
        if options[Options.InitialsBefore] and not first:
            return initials + " " + surname
        elif options[Options.InitialsNoPeriod]:
            return surname + " " + initials
        else:
            return surname + ", " + initials
