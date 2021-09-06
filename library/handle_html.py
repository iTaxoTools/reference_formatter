#!/usr/bin/env python3

import html
import itertools
import logging
from typing import Tuple, Optional, NamedTuple, Iterator, List

import regex

from library.utils import normalize_space


class TagPosition(NamedTuple):
    start: int
    end: int


class LocatedTag(NamedTuple):
    name: str
    position: TagPosition


def _find_tag(input: str, tag: str) -> Optional[TagPosition]:
    tag_match = regex.search(r'<\s*' + tag + r'[^>]*>', input, flags=regex.IGNORECASE)
    if tag_match:
        return TagPosition(tag_match.start(), tag_match.end())
    else:
        return None


def _next_tag(input: str) -> Optional[LocatedTag]:
    tag_match = regex.search(r'<\s*(\w+)[^>]*>', input, flags=regex.IGNORECASE)
    if tag_match:
        return LocatedTag(tag_match.group(1).casefold(),
                          TagPosition(tag_match.start(), tag_match.end()))
    else:
        return None


def _close_tag(tag: str) -> str:
    tag_name_match = regex.match(r'\s*<\s*(\w+)', tag)
    if not tag_name_match:
        raise ValueError(f"{tag} is not an opening tag")
    return "</" + tag_name_match.group(1) + ">"


def is_closing(tag: str) -> bool:
    return tag[:2] == "</"


class ListEntry(NamedTuple):
    decoration: Optional[str]
    content: str

    @staticmethod
    def construct(entry: str) -> 'ListEntry':
        entry = normalize_space(entry.strip())
        decoration_open_match = regex.match(r'<\s*(\w+)[^>]*>', entry)
        if decoration_open_match:
            entry = entry[decoration_open_match.end():]
            tag_name = decoration_open_match.group(1)
            decoration_close_match = regex.search(r'</\s*' + tag_name + r'\s*>$', entry)
            if decoration_close_match:
                entry = entry[:decoration_close_match.start()].strip()
            return ListEntry(decoration_open_match.group(0), entry)
        else:
            return ListEntry(None, entry)

    def to_str(self) -> str:
        if not self.decoration:
            return self.content
        else:
            return self.decoration + self.content + _close_tag(self.decoration)


class HTMLList():
    """
    Parses HTML document into an iterator over elements of <ul>, <ol> or paragraphs
    """

    UNORDERED = 0
    ORDERED = 1
    PARAGRAPHS = 2

    def __init__(self, document: str):
        self._input = document
        self._separate_preamble()
        self._detect_list_type()

    def __iter__(self) -> Iterator[ListEntry]:
        return self

    def __next__(self) -> ListEntry:
        if self._list_type == HTMLList.PARAGRAPHS:
            return self._paragraphs_next()
        else:
            return self._list_next()

    def assemble_html(self, list: Iterator[ListEntry]) -> Iterator[str]:
        """
        Puts list entries in `list` back into the input html
        """
        yield self.preamble
        if self._list_type == HTMLList.UNORDERED:
            list_tag: Optional[str] = "<ul>"
        elif self._list_type == HTMLList.ORDERED:
            list_tag = "<ol>"
        else:
            list_tag = None
        if list_tag:
            yield "\t" * 2 + list_tag
        for entry in list:
            if list_tag:
                yield "\t" * 3 + "<li>"
            yield "\t" * 4 + entry.to_str()
            if list_tag:
                yield "\t" * 3 + "</li>"
        if list_tag:
            yield "\t" * 2 + _close_tag(list_tag)
        yield "\t</body>\n</html>"

    def _separate_preamble(self) -> None:
        located_body = _find_tag(self._input, 'body')
        if not located_body:
            self.preamble = ""
            return
        self.preamble = self._input[:located_body.end]
        self._input = self._input[located_body.end:]
        located_body_end = _find_tag(self._input, '/body')
        if located_body_end:
            self._input = self._input[:located_body_end.start]

    def _detect_list_type(self) -> None:
        first_body_tag = _next_tag(self._input)
        if not first_body_tag:
            logging.error("Can't detect the structure of the reference list")
            raise ValueError("Can't detect the structure of the reference list")
        if first_body_tag.name == "ul":
            self._list_type = HTMLList.UNORDERED
        elif first_body_tag.name == "ol":
            self._list_type = HTMLList.ORDERED
        elif first_body_tag.name == "p":
            self._list_type = HTMLList.PARAGRAPHS
        else:
            self._input = self._input[first_body_tag.position.end:]
            self._detect_list_type()

    def _list_next(self) -> ListEntry:
        li_tag = _find_tag(self._input, "li")
        if not li_tag:
            raise StopIteration
        self._input = self._input[li_tag.end:]
        close_li_tag = _find_tag(self._input, "/li")
        next_li_tag = _find_tag(self._input, "li")
        if not close_li_tag and not next_li_tag:
            if self._list_type == HTMLList.UNORDERED:
                end_list_tag = _find_tag(self._input, "/ul")
            elif self._list_type == HTMLList.ORDERED:
                end_list_tag = _find_tag(self._input, "/ol")
            else:
                assert False
            if end_list_tag:
                entry_content = self._input[:end_list_tag.start]
            else:
                entry_content = self._input
            return ListEntry.construct(entry_content)
        if close_li_tag:
            entry_content = self._input[:close_li_tag.start]
            self._input = self._input[close_li_tag.end:]
        elif next_li_tag:
            entry_content = self._input[:next_li_tag.start]
            self._input = self._input[next_li_tag.start:]
        else:
            assert False
        return ListEntry.construct(entry_content)

    def _paragraphs_next(self) -> ListEntry:
        p_tag = _find_tag(self._input, "p")
        if not p_tag:
            raise StopIteration
        p_description = self._input[p_tag.start:p_tag.end]
        self._input = self._input[p_tag.end:]
        close_p_tag = _find_tag(self._input, "/p")
        next_p_tag = _find_tag(self._input, "p")
        if close_p_tag:
            entry_content = p_description + self._input[:close_p_tag.end]
            self._input = self._input[close_p_tag.end:]
        elif next_p_tag:
            entry_content = p_description + self._input[:next_p_tag.start]
            self._input = self._input[next_p_tag.start:]
        else:
            entry_content = p_description + self._input
            self._input = ""
        return ListEntry.construct(entry_content)


class ExtractedTags:

    def __init__(self, parts: List[str], tags: List[str]):
        self._tags: List[Tuple[int, str]] = list(zip(map(len, parts), tags))

    def surround_tags(self, s: str, offset: int) -> str:
        opened_tags: List[str] = []
        for tag_offset, tag in self._tags:
            if tag_offset > offset:
                break
            if is_closing(tag):
                if opened_tags:
                    opened_tags.pop()
            else:
                opened_tags.append(tag)
        return "".join(itertools.chain(opened_tags, [s], map(_close_tag, reversed(opened_tags))))

    def insert_tags(self, s: str, offset: int) -> str:
        if not self._tags:
            return s
        total_offset = - offset
        parts: List[str] = []
        for tag_offset, tag in self._tags:
            if total_offset + tag_offset < 0:
                total_offset += tag_offset
                continue
            if total_offset + tag_offset > len(s):
                break
            part_start = total_offset if total_offset >= 0 else 0
            parts.append(html.escape(s[part_start:total_offset + tag_offset]))
            parts.append(tag)
            total_offset += tag_offset
        parts.append(s[total_offset:])
        return "".join(parts)


def extract_tags(s: str) -> Tuple[str, ExtractedTags]:
    """
    Returns HTML-unescaped string without tags
    and an object containing extracted tags with their positions
    """
    tag_regex = regex.compile(r'<[^>]*>')
    tags: List[str] = list(map(lambda m: m.group(), regex.finditer(tag_regex, s)))
    parts: List[str] = list(map(html.unescape, regex.splititer(tag_regex, s)))
    assert parts
    return ("".join(parts), ExtractedTags(parts, tags))
