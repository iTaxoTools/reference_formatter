#!/usr/bin/env python
from __future__ import annotations

from enum import IntEnum, Enum
from typing import (
    Dict,
    List,
    Optional,
    Iterator,
    Any,
    TextIO,
    Tuple,
    Union,
    Set,
    NamedTuple,
)
import os

import regex  # type: ignore

from .utils import normalize_space, replace_slice
from .journal_list import JournalMatcher, NameForm
from .handle_html import ExtractedTags, HTMLList, extract_tags, ListEntry
from .positioned import PositionedString
from .crossref import doi_from_title
from .options import OptionsDict, Options, Style, LastSeparator, JournalSeparator
from .author import Author
from .journal import Journal
from .doi import parse_doi


class YearPosition(Enum):
    Medial = 0
    Terminal = 1


REFERENCE_FIELD_COUNT = 10


class Reference(NamedTuple):
    numbering: Optional[slice]
    authors: Tuple[Optional[List[Author]], slice]
    year: Tuple[str, slice, YearPosition]
    article: slice
    journal_separator: Optional[slice]
    journal: Optional[Tuple[Journal, slice]]
    volume_separator: Optional[slice]
    volume: Optional[Tuple[str, Optional[str], slice]]
    page_range: Optional[Tuple[str, str, slice]]
    doi: Optional[slice]
    unparsed: str

    def append_doi(self, doi: str) -> None:
        start = len(self.unparsed)
        end = start + len(doi)
        self._replace(unparsed=(self.unparsed + doi), doi=slice(start, end))

    def format_authors(
        self, options: OptionsDict, tags: ExtractedTags, input: str
    ) -> str:
        authors, authors_span = self.authors
        if not authors:
            return input
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
            replacement = last_author + end_sep
        else:
            replacement = (
                ", ".join(authors_str)
                + str(options[Options.LastNameSep])
                + last_author
                + end_sep
            )
        return replace_slice(input, authors_span, replacement)

    def format_numbering(self, options: OptionsDict, input: str) -> str:
        if not options[Options.KeepNumbering] and self.numbering:
            return replace_slice(input, self.numbering, "")
        else:
            return input

    def format_doi(self, options: OptionsDict, input: str) -> str:
        if options[Options.RemoveDoi]:
            if self.doi:
                return replace_slice(input, self.doi, "")
            else:
                return input
        elif options[Options.CrossrefAPI] and not self.doi:
            retrieved_doi = doi_from_title(
                self.unparsed[self.article], options[Options.CrossrefAPI].is_fuzzy()
            )
            if retrieved_doi:
                return input + " " + retrieved_doi
            else:
                return input
        else:
            return input

    def format_terminal_year(self, options: OptionsDict, input: str) -> str:
        if self.year[2] == YearPosition.Terminal:
            return replace_slice(input, self.year[1], "")
        else:
            return input

    def year_gap(self) -> slice:
        _, authors_slice = self.authors
        _, authors_stop, _ = authors_slice.indices(len(self.unparsed))
        article_start, _, _ = self.article.indices(len(self.unparsed))
        return slice(authors_stop, article_start)

    def format_year(self, options: OptionsDict, input: str) -> str:
        year, span, year_position = self.year
        if year_position == YearPosition.Terminal:
            span = self.year_gap()
        formatted_year = options[Options.YearFormat].format_year(self.year[0])
        return replace_slice(input, span, formatted_year + " ")

    def format_article(
        self, options: OptionsDict, tags: Optional[ExtractedTags], input: str
    ) -> str:
        article = self.unparsed[self.article]
        article_position = self.article.indices(len(self.unparsed))[0]
        if not tags:
            return input
        else:
            return replace_slice(
                input, self.article, tags.insert_tags(article, article_position)
            )

    def format_journal(
        self, options: OptionsDict, tags: ExtractedTags, input: str
    ) -> str:
        if self.journal:
            journal, span = self.journal
            return replace_slice(input, span, journal.format(options, tags, span))
        else:
            return input

    def format_journal_separator(self, options: OptionsDict, input: str) -> str:
        if (
            self.journal_separator
            and options[Options.JournalSeparator] != JournalSeparator.Unchanged
        ):
            return replace_slice(
                input,
                self.journal_separator,
                options[Options.JournalSeparator].format() + " ",
            )
        else:
            return input

    def format_volume_separator(self, options: OptionsDict, input: str) -> str:
        if self.volume_separator:
            return replace_slice(
                input, self.volume_separator, options[Options.VolumeSeparator].format()
            )
        else:
            return input

    def format_volume(self, options: OptionsDict, input: str) -> str:
        if not self.volume:
            return input
        volume, issue, span = self.volume
        formatted_issue = f" ({issue})" if issue else ""
        formatted_volume = (
            volume
            + ("" if options[Options.RemoveIssue] else formatted_issue)
            + options[Options.VolumeFormatting].format()
        )
        if (
            options[Options.HtmlFormat]
            and options[Options.VolumeStyle] != Style.Preserve
        ):
            formatted_volume = options[Options.VolumeStyle].style(formatted_volume)
        return replace_slice(input, span, formatted_volume)

    def format_page_range(self, options: OptionsDict, input: str) -> str:
        if self.page_range:
            page_start, page_end, slice = self.page_range
            formatted_range = options[Options.PageRangeSeparator].format_range(
                (page_start, page_end)
            )
            return replace_slice(input, slice, formatted_range)
        else:
            return input

    def collect_slices(self) -> List[slice]:
        """
        asserts that all parts of the reference are in the expected order
        """
        slices: List[slice] = []
        if self.numbering:
            slices.append(self.numbering)
        slices.append(self.authors[1])
        if self.year[2] == YearPosition.Medial:
            slices.append(self.year[1])
        slices.append(self.article)
        if self.journal_separator:
            slices.append(self.journal_separator)
        if self.journal:
            slices.append(self.journal[1])
        if self.volume_separator:
            slices.append(self.volume_separator)
        if self.volume:
            slices.append(self.volume[2])
        if self.page_range:
            slices.append(self.page_range[2])
        if self.year[2] == YearPosition.Terminal:
            slices.append(self.year[1])
        if self.doi:
            slices.append(self.doi)
        return slices

    def assert_parts_order(self, slices: List[slice]):
        """
        asserts that all parts of the reference are in the expected order
        """
        for i in range(len(slices) - 1):
            assert slices[i].stop <= slices[i + 1].start

    def serialize(self, brackets: str) -> str:
        open_bracket, close_bracket = tuple(brackets)
        slices = self.collect_slices()
        result = self.unparsed
        for sl in reversed(slices):
            start, stop, _ = sl.indices(len(result))
            result = (
                result[:start]
                + open_bracket
                + result[start:stop]
                + close_bracket
                + result[stop:]
            )
        fields: List[Any] = [
            self.numbering,
            self.authors,
            self.article,
            self.journal_separator,
            self.journal,
            self.volume_separator,
            self.volume,
            self.page_range,
            self.doi,
        ]
        if self.year[2] == YearPosition.Terminal:
            fields.insert(8, self.year)
        else:
            fields.insert(2, self.year)
        for item in fields:
            if item is None:
                result += "0"
            else:
                result += "1"
        if self.year[2] == YearPosition.Terminal:
            result += "t"
        else:
            result += "m"
        return result

    @staticmethod
    def extract_slice(input: str, brackets: Tuple[str, str]) -> Tuple[str, slice]:
        open_bracket, close_bracket = brackets
        open_index = input.find(open_bracket)
        close_index = input.find(close_bracket)
        input = (
            input[:open_index]
            + input[open_index + 1 : close_index]
            + input[close_index + 1 :]
        )
        return (input, slice(open_index, close_index - 1))

    @staticmethod
    def deserialize(
        input: str, brackets: str, journal_matcher: Optional[JournalMatcher]
    ) -> Reference:
        open_bracket, close_bracket = tuple(brackets)
        if input[-1] == "t":
            year_position = YearPosition.Terminal
        else:
            year_position = YearPosition.Medial
        input = input[:-1]
        optionals = [c == "1" for c in input[-REFERENCE_FIELD_COUNT:]]
        input = input[:-REFERENCE_FIELD_COUNT]
        slices: List[Optional[slice]] = []
        for present in optionals:
            if present:
                input, a_slice = Reference.extract_slice(
                    input, (open_bracket, close_bracket)
                )
                slices.append(a_slice)
            else:
                slices.append(None)
        return Reference.from_slices(slices, input, journal_matcher, year_position)

    @staticmethod
    def from_slices(
        slices: List[Optional[slice]],
        input: str,
        journal_matcher: Optional[JournalMatcher],
        year_position: YearPosition,
    ) -> Reference:
        parsers = [
            ("numbering", Reference._numbering_from_slice),
            ("authors", Reference._authors_from_slice),
            ("article", Reference._article_from_slice),
            ("journal_separator", Reference._journal_separator_from_slice),
            ("journal", Reference._journal_from_slice),
            ("volume_separator", Reference._volume_separator_from_slice),
            ("volume", Reference._volume_from_slice),
            ("page_range", Reference._page_range_from_slice),
            ("doi", Reference._doi_from_slice),
        ]
        if year_position == YearPosition.Terminal:
            parsers.insert(8, ("year", Reference._year_from_slice))
        else:
            parsers.insert(2, ("year", Reference._year_from_slice))
        ref_dict = {
            field_name: field_parser(slices[i], input, journal_matcher)
            if slices[i]
            else None
            for i, (field_name, field_parser) in enumerate(parsers)
        }
        year_as_list = list(ref_dict["year"])
        year_as_list[2] = year_position
        ref_dict["year"] = tuple(year_as_list)
        ref_dict["unparsed"] = input
        return Reference(**ref_dict)

    @staticmethod
    def _numbering_from_slice(
        a_slice: slice, _: str, journal_matcher: Optional[JournalMatcher]
    ) -> slice:
        return a_slice

    @staticmethod
    def _authors_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> Tuple[Optional[List[Author]], slice]:
        start, end, _ = a_slice.indices(len(input))
        positioned_authors = PositionedString(input[a_slice], start, end)
        return Reference.parse_authors(positioned_authors), a_slice

    @staticmethod
    def _year_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> Tuple[str, slice, YearPosition]:
        year_string = regex.search(r"\d+[a-z]?", input[a_slice]).group(0)
        return year_string, a_slice, YearPosition.Medial

    @staticmethod
    def _article_from_slice(
        a_slice: slice, _: str, journal_matcher: Optional[JournalMatcher]
    ) -> slice:
        return a_slice

    @staticmethod
    def _journal_separator_from_slice(
        a_slice: slice, _: str, journal_matcher: Optional[JournalMatcher]
    ) -> slice:
        return a_slice

    @staticmethod
    def _journal_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> Tuple[Journal, slice]:
        if journal_matcher is None:
            return None, a_slice
        journal_name_tuple = journal_matcher.extract_journal(input[a_slice])
        if journal_name_tuple is None:
            return None, a_slice
        journal_name, _ = journal_name_tuple
        return Journal(journal_name), a_slice

    @staticmethod
    def _volume_separator_from_slice(
        a_slice: slice, _: str, journal_matcher: Optional[JournalMatcher]
    ) -> slice:
        return a_slice

    @staticmethod
    def _volume_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> Tuple[str, Optional[str], slice]:
        volume_regex = regex.compile(
            r"(?<vol>\d+)[,:]|"
            r"(?<vol>\d+)\s*\((?<issue>\d[^)])\)|"
            r"vol\S+\s*(?<vol>d+)\s*iss\S+\s*(?<issue>\d+)"
        )
        volume_match = regex.fullmatch(volume_regex, input[a_slice])
        return volume_match.group("vol"), volume_match.group("issue"), a_slice

    @staticmethod
    def _page_range_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> Tuple[str, str, slice]:
        page_range_regex = regex.compile(
            r"(?:pp\.)?\s*([A-Za-z]*\d+)\s?[-‐‑‒–—―]\s?([A-Za-z]*\d+)\S?$"
        )
        page_range_match = regex.fullmatch(page_range_regex, input[a_slice])
        return (
            page_range_match.group(1).strip(),
            page_range_match.group(2).strip(),
            a_slice,
        )

    @staticmethod
    def _doi_from_slice(
        a_slice: slice, input: str, journal_matcher: Optional[JournalMatcher]
    ) -> slice:
        return a_slice

    def format_reference(self, options: OptionsDict, tags: Optional[ExtractedTags]):
        self.assert_parts_order(self.collect_slices())
        formatted_reference = self.unparsed
        formatted_reference = self.format_doi(options, formatted_reference)
        if options[Options.ProcessAuthorsAndYear]:
            formatted_reference = self.format_terminal_year(
                options, formatted_reference
            )
        if options[Options.ProcessPageRangeVolume]:
            formatted_reference = self.format_page_range(options, formatted_reference)
            formatted_reference = self.format_volume(options, formatted_reference)
            formatted_reference = self.format_volume_separator(
                options, formatted_reference
            )
        if options[Options.ProcessJournalName]:
            formatted_reference = self.format_journal(
                options, tags, formatted_reference
            )
            formatted_reference = self.format_journal_separator(
                options, formatted_reference
            )
        formatted_reference = self.format_article(options, tags, formatted_reference)
        if options[Options.ProcessAuthorsAndYear]:
            formatted_reference = self.format_year(options, formatted_reference)
            formatted_reference = self.format_authors(
                options, tags, formatted_reference
            )
        formatted_reference = self.format_numbering(options, formatted_reference)
        return normalize_space(formatted_reference).strip()

    @staticmethod
    def parse(
        line: str, journal_matcher: Optional[JournalMatcher]
    ) -> Optional["Reference"]:
        s = PositionedString.new(line)
        s, doi = parse_doi(s)
        numbering_match = s.match(r"\d+\.?\s*")
        if numbering_match:
            _, numbering_str, s = s.match_partition(numbering_match)
            numbering = numbering_str.get_slice()
            s = s.strip()
        else:
            numbering = None
        terminal_year_match = s.search(r"\((\d+[a-z]?)\)\S?$")
        if terminal_year_match:
            authors_article = Reference.split_three_words(
                s[: terminal_year_match.start()]
            )
            if authors_article:
                authors, article = authors_article
            else:
                return None
            year = (
                terminal_year_match.group(1),
                s.match_position(terminal_year_match),
                YearPosition.Terminal,
            )
        else:
            year_match = s.search(r"\(?(\d+[a-z]?)\)?\S?")
            if not year_match:
                return None
            authors, year_string, article = s.match_partition(year_match)
            year = (
                year_match.group(1),
                year_string.get_slice(),
                YearPosition.Medial,
            )
        authors = authors.strip()
        article = article.strip()
        page_range_regex = regex.compile(
            r"(?:pp\.)?\s*([A-Za-z]*\d+)\s?[-‐‑‒–—―]\s?([A-Za-z]*\d+)\S?$"
        )
        page_range_match = article.search(page_range_regex)
        if page_range_match:
            article, page_range_string, _ = article.match_partition(page_range_match)
            page_range: Optional[Tuple[str, str, slice]] = (
                page_range_match.group(1).strip(),
                page_range_match.group(2).strip(),
                page_range_string.get_slice(),
            )
            article = article.strip()
        else:
            page_range = None
        if journal_matcher:
            journal_name_tuple = journal_matcher.extract_journal(article.content)
            if journal_name_tuple:
                journal_name, journal_span = journal_name_tuple
                extra = article[journal_span.stop :].strip()
                article = article[: journal_span.start]
                journal_separator_match = article.search(r"\W*$")
                article, _, _ = article.match_partition(journal_separator_match)
                journal_separator = article.match_position(journal_separator_match)
                journal_span = slice(
                    article.start + journal_span.start,
                    article.start + journal_span.stop,
                )
                volume_regex = regex.compile(
                    r"(?<vol>\d+)[,:]|"
                    r"(?<vol>\d+)\s*\((?<issue>\d[^)])\)|"
                    r"vol\S+\s*(?<vol>d+)\s*iss\S+\s*(?<issue>\d+)"
                )
                volume_match = extra.search(volume_regex)
                journal: Optional[Tuple[Journal, slice]] = (
                    Journal(journal_name),
                    journal_span,
                )
                if not volume_match:
                    volume = None
                    volume_separator = None
                else:
                    volume_separator = extra[: volume_match.start()].get_slice()
                    journal_volume = (
                        volume_match.group("vol"),
                        volume_match.group("issue"),
                        extra.match_position(volume_match),
                    )
                    volume = journal_volume
                article = article.strip()
            else:
                journal_separator = None
                journal = None
                volume_separator = None
                volume = None
        else:
            journal_separator = None
            journal = None
            volume_separator = None
            volume = None
        try:
            authors_list = (Reference.parse_authors(authors), authors.get_slice())
        except IndexError:  # parts.pop in extract_author
            print("Unexpected name:\n", authors.content)
            return None
        return Reference(
            numbering,
            authors_list,
            year,
            article.get_slice(),
            journal_separator,
            journal,
            volume_separator,
            volume,
            page_range,
            doi,
            line,
        )

    @staticmethod
    def split_three_words(
        s: PositionedString,
    ) -> Optional[Tuple[PositionedString, PositionedString]]:
        three_words_regex = regex.compile(
            r"[^\s.]*[[:lower:]][^\s.]*\s+"
            r"[^\s.]*[[:lower:]][^\s.]*\s+"
            r"[^\s.]*[[:lower:]][^\s.]*"
        )
        three_words_match = s.search(three_words_regex)
        if three_words_regex:
            return s[: three_words_match.start()], s[three_words_match.start() :]
        else:
            return None

    @staticmethod
    def parse_authors(s: PositionedString) -> List[Author]:
        # try to separate the last author
        # after the loop parts_rest and last_part will be comma-separated lists
        # of surnames and initials
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

    @staticmethod
    def extract_author(parts: List[PositionedString]) -> Iterator[Author]:
        while parts:
            part = parts.pop(0)
            if regex.search("et al", part.content):
                yield (Author(part.get_slice()))
                continue
            find_surname = part.search(r"\p{Alpha}[\p{Lower}\'\u2019].*\p{Lower}")
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
                initials = part[find_surname.end() + 1 :].content
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


def txt_to_references(
    input: TextIO,
    options: OptionsDict,
    journal_matcher: Optional[JournalMatcher],
) -> Iterator[Union[Reference, str]]:
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
            yield prev_reference
            prev_reference = None
        elif isinstance(parsed_line, Reference):
            if prev_reference:
                yield prev_reference
            prev_reference = parsed_line
        else:
            yield line
            continue
    if prev_reference:
        yield prev_reference


def txt_first_step(
    input: TextIO,
    output_dir: str,
    options: OptionsDict,
    journal_matcher: Optional[JournalMatcher],
):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        for ref in txt_to_references(input, options, journal_matcher):
            if isinstance(ref, Reference):
                print(ref.serialize("{}"), file=outfile)
            else:
                print("*", ref, file=outfile)


def process_reference_file(
    input: TextIO,
    output_dir: str,
    options: OptionsDict,
    journal_matcher: Optional[JournalMatcher],
):
    with open(os.path.join(output_dir, "output"), mode="w") as outfile:
        for ref in txt_to_references(input, options, journal_matcher):
            if isinstance(ref, Reference):
                print(ref.format_reference(options, None), file=outfile)
            else:
                print("*", ref, file=outfile)


def processed_references(
    html: HTMLList, options: OptionsDict, journal_matcher: Optional[JournalMatcher]
) -> Iterator[ListEntry]:
    for entry in html:
        ref_text, tags = extract_tags(entry.content)
        ref = Reference.parse(ref_text, journal_matcher)
        if not ref:
            yield entry._replace(content=("*" + entry.content))
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
        for chunk in html.assemble_html(
            processed_references(html, options, journal_matcher)
        ):
            print(chunk, file=outfile)
