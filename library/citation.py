#!/usr/bin/env python

from enum import IntEnum, Enum
from typing import Dict, List, Optional, Iterator, Any, TextIO, Tuple, Union
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
    KeepNumbering = (bool, "Keep numbering of references")
    RemoveDoi = (bool, "Remove doi")
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


def parse_doi(line: str) -> Tuple[str, Optional[str]]:
    """
    Parses line as line == rest + doi and returns (rest, doi).
    Returns (line, None) is the line doesn't contain doi
    """
    doi_regex = regex.compile(r"https?:.*doi.*$|\bdoi: ?[^ ]*$")
    doi_match = doi_regex.search(line)
    if doi_match:
        return (line[: doi_match.start()], doi_match.group(0))
    else:
        return (line, None)


class Reference:
    def __init__(
        self,
        numbering: Optional[str],
        authors: List[Author],
        year: int,
        article: str,
        doi: Optional[str],
    ):
        self.numbering = numbering
        self.authors = authors
        self.year = year
        self.article = article
        self.doi = doi

    def format_authors(self, options: OptionsDict):
        if not self.authors:
            return ""
        formatted_authors = (
            author.format_author(options, i == 0)
            for i, author in enumerate(self.authors)
        )
        *authors, last_author = formatted_authors
        if not authors:
            return last_author
        else:
            return ", ".join(authors) + str(options[Options.LastNameSep]) + last_author

    def format_numbering(self, options: OptionsDict) -> str:
        if options[Options.KeepNumbering] and self.numbering:
            return self.numbering
        else:
            return ""

    def format_doi(self, options: OptionsDict) -> str:
        if options[Options.RemoveDoi]:
            return ""
        else:
            return self.doi or ""

    def format_reference(self, options: OptionsDict):
        return (
            self.format_numbering(options)
            + self.format_authors(options)
            + " "
            + options[Options.YearFormat].format_year(self.year)
            + " "
            + self.article
            + self.format_doi(options)
        )

    @staticmethod
    def parse(s: str) -> Optional["Reference"]:
        s, doi = parse_doi(s)
        numbering_match = regex.match(r"\d+\.?\s", s)
        if numbering_match:
            numbering = numbering_match.group(0)
            s = s[numbering_match.end() :]
        else:
            numbering = None
        terminal_year_match = regex.search(r"\(?(\d+)\)?\S?$", s)
        if terminal_year_match:
            authors_article = Reference.split_three_words(
                s[: terminal_year_match.start()]
            )
            if authors_article:
                authors, article = authors_article
            else:
                return None
            year = int(terminal_year_match.group(1))
        else:
            year_match = regex.search(r"\(?(\d+)\)?\S?", s)
            year_start, year_end = year_match.span()
            if not year_match:
                return None
            authors = s[:year_start]
            article = s[year_end:]
            year = int(year_match.group(1))
        try:
            return Reference(
                numbering, Reference.parse_authors(authors), year, article, doi
            )
        except IndexError:  # parts.pop in extract_author
            return None

    @staticmethod
    def split_three_words(s: str) -> Optional[Tuple[str, str]]:
        three_words_regex = regex.compile(
            r"[^\s.]*[[:lower:]][^\s.]*\s+[^\s.]*[[:lower:]][^\s.]*\s+[^\s.]*[[:lower:]][^\s.]*"
        )
        three_words_match = three_words_regex.search(s)
        if three_words_regex:
            return s[: three_words_match.start()], s[three_words_match.start() :]
        else:
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


def parse_line(line: str) -> Union[Optional[Reference], str]:
    (rest, doi) = parse_doi(line)
    if not rest and doi:
        return doi
    else:
        return Reference.parse(line)


def process_reference_file(input: TextIO, output_dir: str, options: OptionsDict):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        prev_reference = None
        for line in input:
            line = line.rstrip()
            if not line:
                continue
            parsed_line = parse_line(line)
            if isinstance(parsed_line, str) and prev_reference:  # line is doi
                prev_reference.doi = "\n" + parsed_line
                print(prev_reference.format_reference(options), file=outfile)
                prev_reference = None
            elif isinstance(parsed_line, Reference):
                if prev_reference:
                    print(prev_reference.format_reference(options), file=outfile)
                prev_reference = parsed_line
            else:
                print("*", line, sep="", file=outfile)
                continue
