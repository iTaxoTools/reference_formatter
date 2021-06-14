#!/usr/bin/env python

from enum import IntEnum, Enum
from typing import Dict, List, Optional, Iterator, Any, TextIO
import os

import regex


class LastSeparator(IntEnum):
    Comma = 0
    Ampersand = 1
    And = 2
    CommaAnd = 3

    def __str__(self) -> str:
        return [", ", " & ", " and ", ", and"][self]


class YearFormat(IntEnum):
    ParenColon = 0
    ParenPeriod = 1
    Paren = 2
    Period = 3
    Colon = 4
    Comma = 5

    def has_paren(self) -> bool:
        return self <= YearFormat.Paren

    def terminator(self) -> str:
        return [":", ".", "", ".", ":", ","][self]

    def format_year(self, year: int) -> str:
        result = str(year)
        if self.has_paren():
            result = "(" + result + ")"
        return result + self.terminator()

    def __str__(self) -> str:
        return self.format_year(1998)


class Options(Enum):
    InitialsBefore = (bool, "Place initials before surname (except first name)")
    InitialsNoPeriod = (bool, "Write initials without abbreviating period")
    LastNameSep = (LastSeparator, "Precede last name with:")
    YearFormat = (YearFormat, "Format year as:")

    def __init__(self, type: type, description: str):
        self.type = type
        self.description = description


OptionsDict = Dict[Options, Any]


def default_options() -> OptionsDict:
    result: OptionsDict = {}
    for option in list(Options):
        if option.type is bool:
            result[option] = False
        elif issubclass(option.type, IntEnum):
            result[option] = option.type(0)
        else:
            assert False
    return result


class Author:
    def __init__(self, surname: str, initials: str):
        self.surname = surname
        self.initials = initials.replace(" ", "")

    def format_author(self, options: OptionsDict, first: bool):
        if options[Options.InitialsNoPeriod]:
            initials = self.initials.replace(".", "")
        else:
            initials = self.initials
        if options[Options.InitialsBefore] and not first:
            return initials + " " + self.surname
        else:
            return self.surname + ", " + initials


class Reference:
    def __init__(self, authors: List[Author], year: int, article: str):
        self.authors = authors
        self.year = year
        self.article = article

    def format_authors(self, options: OptionsDict):
        if not self.authors:
            return ""
        formatted_authors = (author.format_author(options, i == 0)
                             for i, author in enumerate(self.authors))
        *authors, last_author = formatted_authors
        if not authors:
            return last_author
        else:
            return ", ".join(authors) + \
                str(options[Options.LastNameSep]) + last_author

    def format_reference(self, options: OptionsDict):
        return self.format_authors(options) + " " + options[Options.YearFormat].format_year(self.year) + " " + self.article

    @staticmethod
    def parse(s: str) -> Optional['Reference']:
        year_match = regex.search(r'\(?(\d+)\)?\S?', s)
        if not year_match:
            return None
        year_start, year_end = year_match.span()
        authors = s[:year_start]
        year = int(year_match.group(1))
        article = s[year_end:]
        try:
            return Reference(Reference.parse_authors(authors), year, article)
        except IndexError:  # parts.pop in extract_author
            return None

    @staticmethod
    def parse_authors(s: str) -> List[Author]:
        # try to separate the last author
        # after the loop parts_rest and last_part will be comma-separated lists of surnames and initials
        for lastsep in map(str, reversed(list(LastSeparator))):
            parts_rest, sep, last_part = s.partition(lastsep)
            if sep:
                break
        parts = [
            part for part in parts_rest.split(", ") + last_part.split(", ") if part
        ]
        return [author for author in Reference.extract_author(parts)]

    @staticmethod
    def extract_author(parts: List[str]) -> Iterator[Author]:
        while parts:
            part = parts.pop(0)
            find_surname = regex.search(r"[[:upper:]][[:lower:]\'].*[[:lower:]]", part)
            if not find_surname:
                initials = part
                surname = parts.pop(0)
            elif find_surname.span() == (0, len(part)):
                surname = part
                initials = parts.pop(0)
            elif find_surname.start() == 0:
                surname = find_surname.group()
                initials = part[find_surname.end() + 1 :]
            else:
                surname = find_surname.group()
                initials = part[: find_surname.start() - 1]
            yield (Author(surname, initials))


def process_reference_file(input: TextIO, output_dir: str, options: OptionsDict):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        for line in input:
            reference = Reference.parse(line)
            if reference is None:
                outfile.write("*")
                outfile.write(line)
                continue
            outfile.write(reference.format_reference(options))
