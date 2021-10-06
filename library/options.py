#!/usr/bin/env python3

from typing import Tuple, Dict, Any, Set

from enum import IntEnum, Enum

from library.journal_list import NameForm


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


class JournalSeparator(IntEnum):
    Period = 0
    Comma = 1
    PeriodMinus = 2
    PeriodNDash = 3
    CommaMinus = 4
    CommaNDash = 5

    def __str__(self) -> str:
        return [".", ",", ".-", ".–", ",-", ",–"][self]

    def format(self) -> str:
        return str(self)


class VolumeSeparator(IntEnum):
    Space = 0
    Period = 1
    Comma = 2
    Semicolon = 3

    def __str__(self) -> str:
        return ["", ".", ",", ";"][self]

    def format(self) -> str:
        return str(self)


class VolumeFormatting(IntEnum):
    Colon = 0
    Comma = 1
    Period = 2
    Semicolon = 3

    def __str__(self) -> str:
        return [":", ",", ".", ";"][self]

    def format(self) -> str:
        return str(self)


class PageSeparator(IntEnum):
    Minus = 0
    Hyphen = 1
    FigureDash = 2
    EnDash = 3
    EmDash = 4

    def __str__(self) -> str:
        return [
            "Minus sign: -",
            "Hyphen: ‐",
            "Figure dash: ‒",
            "En dash: –",
            "Em dash: —",
        ][self]

    def format_range(self, range: Tuple[str, str]) -> str:
        start, end = range
        return start + "-‐‒–—"[self] + end


class Style(IntEnum):
    Preserve = 0
    Normal = 1
    Italics = 2
    Bold = 3
    SmallCaps = 4

    def __str__(self) -> str:
        return [
            "preserve",
            "normal",
            "italics",
            "bold",
            "small caps"
        ][self]

    def style(self, s: str) -> str:
        tags = [
            ("", ""),
            ("", ""),
            ("<i>", "</i>"),
            ("<b>", "</b>"),
            ("<span style=\"font-variant: small-caps\">", "</span>")
        ]
        return tags[self][0] + s + tags[self][1]


class CrossrefMatch(IntEnum):
    NotUsed = 0
    Exact = 1
    Fuzzy = 2

    def __str__(self) -> str:
        return [
            "No DOI retrieval",
            "Retrieve DOIs by strict title match",
            "Retrieve DOIs by fuzzy title match",
        ][self]

    def __bool__(self) -> bool:
        return self != CrossrefMatch.NotUsed

    def is_fuzzy(self) -> bool:
        return self == CrossrefMatch.Fuzzy


class Options(Enum):
    ProcessAuthorsAndYear = (bool, "Convert authors and year of publication")
    ProcessPageRangeVolume = (bool, "Convert page range and volume/issue number")
    ProcessJournalName = (bool, "Convert journal name")
    InitialsBefore = (bool, "Place initials before surname (except first name)")
    InitialsNoPeriod = (bool, "Write initials without abbreviating period")
    KeepNumbering = (bool, "Keep numbering of references")
    RemoveDoi = (bool, "Remove doi")
    LastNameSep = (LastSeparator, "Precede last name with:")
    YearFormat = (YearFormat, "Format year as:")
    JournalSeparator = (JournalSeparator, "Separate Journal name with:")
    JournalNameForm = (NameForm, "Represent journal name as:")
    VolumeSeparator = (VolumeSeparator, "Separate volume number with:")
    RemoveIssue = (bool, "Remove issue number")
    VolumeFormatting = (
        VolumeFormatting,
        "Format volume number (and issue number) with:",
    )
    PageRangeSeparator = (PageSeparator, "Use as page range separator")
    CrossrefAPI = (CrossrefMatch, "Retrieve missing DOIs from Crossref")
    HtmlFormat = (bool, "HTML format")
    SurnameStyle = (Style, "Style authors' surnames")
    JournalStyle = (Style, "Style journal name")
    VolumeStyle = (Style, "Style volume number")

    def __init__(self, type: type, description: str):
        self.type = type
        self.description = description


options_on_by_default: Set[Options] = {
    Options.ProcessAuthorsAndYear,
    Options.ProcessPageRangeVolume,
    Options.ProcessJournalName,
}

OptionsDict = Dict[Options, Any]


def default_options() -> OptionsDict:
    result: OptionsDict = {}
    for option in list(Options):
        if option.type is bool:
            result[option] = option in options_on_by_default
        elif issubclass(option.type, IntEnum):
            result[option] = option.type(0)
        else:
            assert False
    return result
