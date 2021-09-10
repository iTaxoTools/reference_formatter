#!/usr/bin/env python

from enum import IntEnum, Enum
from typing import Dict, List, Optional, Iterator, Any, TextIO, Tuple, Union, Set, NamedTuple
import os

import regex

from library.utils import *
from library.journal_list import JournalMatcher, NameForm
from library.handle_html import ExtractedTags, HTMLList, extract_tags, ListEntry
from library.positioned import PositionedString
from library.crossref import doi_from_title


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


class Author:
    def __init__(self, span: slice, surname: Optional[str] = None, initials: Optional[str] = None):
        if surname is None or initials is None:
            self.is_et_al = True
            return
        self.is_et_al = False
        self.surname = surname
        self.initials = initials.replace(" ", "")
        self.span = span

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
        else:
            return surname + ", " + initials


def parse_doi(line: PositionedString) -> Tuple[PositionedString, Optional[slice]]:
    """
    Parses line as line == rest + doi and returns (rest, doi).
    Returns (line, None) is the line doesn't contain doi
    """
    doi_regex = regex.compile(r"https?:.*doi.*$|\bdoi: ?[^ ]*$")
    doi_match = line.search(doi_regex)
    if doi_match:
        rest, doi, _ = line.match_partition(doi_match)
        return rest, doi.get_slice()
    else:
        return (line, None)


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


class Reference(NamedTuple):
    numbering: Optional[slice]
    authors: Tuple[Optional[List[Author]], slice]
    year: Tuple[int, slice]
    article: slice
    journal: Optional[Tuple[Journal, slice]]
    volume: Optional[Tuple[str, Optional[str], slice]]
    extra: slice
    page_range: Optional[Tuple[str, str, slice]]
    doi: Optional[slice]
    unparsed: str

    def append_doi(self, doi: str) -> None:
        start = len(self.unparsed)
        end = start + len(doi)
        self._replace(unparsed=(self.unparsed + doi), doi=slice(start, end))

    def format_authors(self, options: OptionsDict, tags: ExtractedTags) -> str:
        authors, authors_span = self.authors
        if (not options[Options.ProcessAuthorsAndYear]) or not authors:
            return self.unparsed[authors_span]
        formatted_authors = (
            author.format_author(options, i == 0, tags)
            for i, author in enumerate(authors)
        )
        *authors_str, last_author = formatted_authors
        if not options[Options.YearFormat].has_paren():
            if options[Options.InitialsBefore] or options[Options.InitialsNoPeriod]:
                end_sep = "."
            else:
                end_sep = ""
        else:
            end_sep = ""
        if not authors_str:
            return last_author + end_sep
        else:
            return (
                ", ".join(authors_str)
                + str(options[Options.LastNameSep])
                + last_author
                + end_sep
            )

    def format_numbering(self, options: OptionsDict) -> str:
        if options[Options.KeepNumbering] and self.numbering:
            return self.unparsed[self.numbering]
        else:
            return ""

    def format_doi(self, options: OptionsDict) -> str:
        if options[Options.RemoveDoi]:
            return ""
        elif options[Options.CrossrefAPI] and not self.doi:
            return doi_from_title(self.unparsed[self.article], options[Options.CrossrefAPI].is_fuzzy()) or ""
        else:
            return self.unparsed[self.doi or slice(0, 0)]

    def format_year(self, options: OptionsDict) -> str:
        if options[Options.ProcessAuthorsAndYear]:
            return options[Options.YearFormat].format_year(self.year[0])
        else:
            return self.unparsed[self.year[1]]

    def format_article(self, options: OptionsDict, tags: Optional[ExtractedTags]) -> str:
        article = self.unparsed[self.article]
        article_position = self.article.indices(len(self.unparsed))[0]
        if not tags:
            return article
        else:
            return tags.insert_tags(article, article_position)

    def format_journal(self, options: OptionsDict, tags: ExtractedTags) -> str:
        if self.journal:
            if options[Options.ProcessJournalName]:
                return self.journal[0].format(options, tags, self.journal[1])
            else:
                return self.unparsed[self.journal[1]]
        else:
            return ""

    def format_volume(self, options: OptionsDict) -> str:
        if not self.volume:
            return ""
        if not options[Options.ProcessPageRangeVolume]:
            return self.unparsed[self.volume[2]]
        volume, issue, span = self.volume
        formatted_issue = f" ({issue})" if issue else ""
        formatted_volume = (
            volume
            + (formatted_issue if options[Options.RemoveIssue] else "")
            + options[Options.VolumeFormatting].format()
        )
        if options[Options.HtmlFormat] and options[Options.VolumeStyle] != Style.Preserve:
            formatted_volume = options[Options.VolumeStyle].style(formatted_volume)
        return formatted_volume

    def format_page_range(self, options: OptionsDict) -> str:
        if self.page_range:
            page_start, page_end, slice = self.page_range
            if options[Options.ProcessPageRangeVolume]:
                return options[Options.PageRangeSeparator].format_range((page_start, page_end))
            else:
                return self.unparsed[slice]
        else:
            return ""

    def format_reference(self, options: OptionsDict, tags: Optional[ExtractedTags]):
        return (
            self.format_numbering(options)
            + " "
            + self.format_authors(options, tags)
            + " "
            + self.format_year(options)
            + " "
            + self.format_article(options, tags)
            + self.format_journal(options, tags)
            + " "
            + self.format_volume(options)
            + " "
            + self.format_page_range(options)
            + " "
            + self.format_doi(options)
        ).strip()

    @staticmethod
    def parse(
        line: str, journal_matcher: Optional[JournalMatcher]
    ) -> Optional["Reference"]:
        s = PositionedString.new(line)
        s, doi = parse_doi(s)
        numbering_match = s.match(r"\d+\.?\s")
        if numbering_match:
            _, numbering, s = s.match_partition(numbering_match)
            numbering = numbering.strip().get_slice()
            s = s.strip()
        else:
            numbering = None
        terminal_year_match = s.search(r"\((\d+)\)\S?$")
        if terminal_year_match:
            authors_article = Reference.split_three_words(
                s[: terminal_year_match.start()]
            )
            if authors_article:
                authors, article = authors_article
            else:
                return None
            year = (int(terminal_year_match.group(1)), slice(
                terminal_year_match.start(), terminal_year_match.end()))
        else:
            year_match = s.search(r"\(?(\d+)\)?\S?")
            if not year_match:
                return None
            authors, year_string, article = s.match_partition(year_match)
            year = (int(year_match.group(1)), year_string.get_slice())
        authors = authors.strip()
        article = article.strip()
        page_range_regex = regex.compile(
            r"(?:pp\.)?\s*([A-Za-z]*\d+)\s?[-‐‑‒–—―]\s?([A-Za-z]*\d+)\S?$"
        )
        page_range_match = article.search(page_range_regex)
        if page_range_match:
            article, page_range_string, _ = article.match_partition(page_range_match)
            page_range = (
                page_range_match.group(1).strip(),
                page_range_match.group(2).strip(),
                page_range_string.get_slice()
            )
            article = article.strip()
        else:
            page_range = None
        if journal_matcher:
            journal_name_tuple = journal_matcher.extract_journal(
                article.content
            )
            if journal_name_tuple:
                journal_name, journal_span = journal_name_tuple
                extra = article[journal_span.stop:].strip()
                article = article[:journal_span.start]
                journal_span = slice(article.start + journal_span.start,
                                     article.start + journal_span.stop)
                volume_regex = regex.compile(
                    r"(?<vol>\d+)[,:]|(?<vol>\d+)\s*\((?<issue>\d[^)])\)|vol\S+\s*(?<vol>d+)\s*iss\S+\s*(?<issue>\d+)"
                )
                volume_match = extra.search(volume_regex)
                if not volume_match:
                    journal = (
                        Journal(journal_name, None),
                        journal_span
                    )
                    volume = None
                else:
                    journal_extra = extra[: volume_match.start()].strip()
                    journal_volume = (
                        volume_match.group("vol"),
                        volume_match.group("issue"),
                        extra.match_position(volume_match)
                    )
                    extra = extra[volume_match.end():].strip().get_slice()
                    journal = (
                        Journal(journal_name, journal_extra.content),
                        journal_span
                    )
                    volume = journal_volume
                article = article.strip()
                if article and regex.match(r"\p{Punct}", article[-1].content):
                    article = article[:-1]
            else:
                journal = None
                volume = None
                extra = slice(0, 0)
        else:
            journal = None
            volume = None
            extra = slice(0, 0)
        try:
            authors_list = (
                Reference.parse_authors(authors),
                authors.get_slice()
            )
        except IndexError:  # parts.pop in extract_author
            print("Unexpected name:\n", authors.content)
            authors_list = (None, authors.get_slice())
        return Reference(
            numbering,
            authors_list,
            year,
            article.get_slice(),
            journal,
            volume,
            extra,
            page_range,
            doi,
            line
        )

    @ staticmethod
    def split_three_words(s: PositionedString) -> Optional[Tuple[PositionedString, PositionedString]]:
        three_words_regex = regex.compile(
            r"[^\s.]*[[:lower:]][^\s.]*\s+[^\s.]*[[:lower:]][^\s.]*\s+[^\s.]*[[:lower:]][^\s.]*"
        )
        three_words_match = s.search(three_words_regex)
        if three_words_regex:
            return s[:three_words_match.start()], s[three_words_match.start():]
        else:
            return None

    @ staticmethod
    def parse_authors(s: PositionedString) -> List[Author]:
        # try to separate the last author
        # after the loop parts_rest and last_part will be comma-separated lists of surnames and initials
        for lastsep in map(str, reversed(list(LastSeparator))):
            parts_rest, sep, last_part = s.partition(lastsep)
            if sep.is_nonempty():
                break
        parts = [
            part.strip()
            for part in parts_rest.split(",") + last_part.split(",")
            if part
        ]
        return [author for author in Reference.extract_author(parts)]

    @ staticmethod
    def extract_author(parts: List[PositionedString]) -> Iterator[Author]:
        while parts:
            part = parts.pop(0)
            if regex.search("et al", part.content):
                yield (Author(part.get_slice()))
                continue
            find_surname = part.search(
                r"\p{Alpha}[\p{Lower}\'\u2019].*\p{Lower}"
            )
            if not find_surname:
                initials = part.content
                surname_pos = parts.pop(0)
                surname = surname_pos.content
                surname_span = surname_pos.get_slice()
            elif find_surname.span() == (0, len(part)):
                surname = part.content
                surname_span = part.get_slice()
                initials = parts.pop(0).content
            elif find_surname.start() == 0:
                surname_pos = part.group(find_surname)
                surname = surname_pos.content
                surname_span = surname_pos.get_slice()
                initials = part[find_surname.end() + 1:].content
            else:
                surname_pos = part.group(find_surname)
                surname = surname_pos.content
                surname_span = surname_pos.get_slice()
                initials = part[: find_surname.start() - 1].content
            yield (Author(surname_span, surname, initials))


def parse_line(
    line: str, journal_matcher: Optional[JournalMatcher]
) -> Union[Optional[Reference], str]:
    (rest, doi) = parse_doi(PositionedString.new(line))
    if not rest and doi:
        return line[doi]
    else:
        return Reference.parse(line, journal_matcher)


def process_reference_file(
    input: TextIO,
    output_dir: str,
    options: OptionsDict,
    journal_matcher: Optional[JournalMatcher],
):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        prev_reference = None
        for line in input:
            if line[0] == "\ufeff":
                line = line[1:]
            line = normalize_space(line.rstrip())
            if not line:
                continue
            parsed_line = parse_line(line, journal_matcher)
            if isinstance(parsed_line, str) and prev_reference:  # line is doi
                prev_reference.doi = "\n" + parsed_line
                prev_reference.replace_doi("\n" + parsed_line)
                print(prev_reference.format_reference(options, None), file=outfile)
                prev_reference = None
            elif isinstance(parsed_line, Reference):
                if prev_reference:
                    print(prev_reference.format_reference(options, None), file=outfile)
                prev_reference = parsed_line
            else:
                print("*", line, sep="", file=outfile)
                continue
        if prev_reference:
            print(prev_reference.format_reference(options, None), file=outfile)


def processed_references(html: HTMLList, options: OptionsDict, journal_matcher: Optional[JournalMatcher]) -> Iterator[ListEntry]:
    for entry in html:
        ref_text, tags = extract_tags(entry.content)
        ref = Reference.parse(ref_text, journal_matcher)
        if not ref:
            yield entry
        else:
            yield entry._replace(content=ref.format_reference(options, tags))


def process_reference_html(
        input: TextIO,
        output_dir: str,
        options: OptionsDict,
        journal_matcher: Optional[JournalMatcher],
):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        html = HTMLList(input.read())
        for chunk in html.assemble_html(processed_references(html, options, journal_matcher)):
            print(chunk, file=outfile)
