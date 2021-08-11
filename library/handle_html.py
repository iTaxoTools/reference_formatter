#!/usr/bin/env python3

import regex
from typing import Tuple, Optional, NamedTuple


class TagPosition(NamedTuple):
    start: int
    end: int


class LocatedTag(NamedTuple):
    name: str
    position: TagPosition


def _find_tag(input: str, tag: str) -> Optional[TagPosition]:
    tag_match = regex.search(r'<\s*' + tag + r'[^>]>', input)
    if tag_match:
        return TagPosition(tag_match.start(), tag_match.end())
    else:
        return None


def _next_tag(input: str, tag: str) -> Optional[LocatedTag]:
    tag_match = regex.search(r'<\s*(\w+)[^>]>', input)
    if tag_match:
        return LocatedTag(tag_match.group(1),
                          TagPosition(tag_match.start(), tag_match.end()))
    else:
        return None


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
        ...
