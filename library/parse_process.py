#!/usr/bin/env python3

from typing import Optional

import regex

from library.options import OptionsDict, Options
from library.doi import parse_doi


class RefProcessor():

    def __init__(self, ref: str):
        self.start = 0
        self.ref = ref

    def numbering(self, options: OptionsDict):
        numbering_match = regex.match(r"\d+\.?\s+")
        if not numbering_match:
            return
        if options[Options.KeepNumbering]:
            self.position = numbering_match.end()
        else:
            self.ref = self.ref[numbering_match.end():]

    def split_doi(self) -> Optional[str]:
        ref, doi_slice = parse_doi(self.ref)
        doi = self.ref[doi_slice]
        self.ref = ref.content
        return doi

    def move_year(self) -> slice:
        """
        Detects year in self.ref,
        moves it between authors and articles,
        formats the year and returns the slice, where it ends up
        """
        ...
