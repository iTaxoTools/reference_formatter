#!/usr/bin/env python3

import html
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


class ListEntry(NamedTuple):
    decoration: Optional[str]
    content: str

    @staticmethod
    def construct(entry: str) -> 'ListEntry':
        entry = normalize_space(entry.strip())
        decoration_match = regex.fullmatch(r'(<\s*(\w+)[^>]*>)(.*?)(</\2>)?', entry)
        if decoration_match:
            return ListEntry(decoration_match.group(1), decoration_match.group(3))
        else:
            return ListEntry(None, entry)


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
            raise ValueError("The reference list is unstructured")
        if first_body_tag.name == "ul":
            self._list_type = HTMLList.UNORDERED
        elif first_body_tag.name == "ol":
            self._list_type = HTMLList.ORDERED
        elif first_body_tag.name == "p":
            self._list_type = HTMLList.PARAGRAPHS
        else:
            raise ValueError("Can't detect the structure of the reference list")

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

    def insert_tags(self, s: str, offset: int) -> str:
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
