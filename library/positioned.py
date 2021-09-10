#!/usr/bin/env python3

import regex
from typing import NamedTuple, Optional, Union, Any, Tuple, List


class PositionedString(NamedTuple):
    """
    String that remembers it's position
    """
    content: str
    start: int
    end: int

    @staticmethod
    def new(s: str, start: int = 0, end: Optional[int] = None) -> 'PositionedString':
        if end is None:
            end = start + len(s)
        else:
            assert end - start == len(s)
        return PositionedString(content=s, start=start, end=end)

    def __len__(self) -> int:
        return len(self.content)

    def __getitem__(self, index: Union[int, slice]) -> 'PositionedString':
        if isinstance(index, int):
            return PositionedString(self.content[index], index, index + 1)
        elif isinstance(index, slice):
            start, end, stride = index.indices(len(self))
            if stride != 1:
                raise IndexError("stride is not 1")
            return PositionedString.new(self.content[start:end],
                                        self.start + start,
                                        self.start + end)
        else:
            raise TypeError

    def is_nonempty(self) -> bool:
        return bool(self.content)

    def get_slice(self) -> slice:
        return slice(self.start, self.end)

    def strip(self, chars: Optional[str] = None) -> 'PositionedString':
        rstripped = self.content.rstrip(chars)
        new_end = self.end - (len(self.content) - len(rstripped))
        stripped = rstripped.lstrip(chars)
        new_start = self.start + (len(rstripped) - len(stripped))
        return PositionedString.new(stripped, new_start, new_end)

    def match(self, pattern: Union[regex.Pattern, str]) -> Optional['regex.Match']:
        if isinstance(pattern, str):
            return regex.match(pattern, self.content)
        return pattern.match(self.content)

    def search(self, pattern: regex.Pattern) -> Optional['regex.Match']:
        if isinstance(pattern, str):
            return regex.search(pattern, self.content)
        return pattern.search(self.content)

    def match_position(self, match: 'regex.Match', group: int = 0) -> slice:
        return slice(self.start + match.start(group), self.start + match.end(group))

    def group(self, match: Optional['regex.Match'], group: int = 0) -> Optional['PositionedString']:
        if not match:
            return None
        return self[match.start(group):match.end(group)]

    def match_partition(self, match: Optional['regex.Match'], group: int = 0) -> Optional[Tuple['PositionedString', 'PositionedString', 'PositionedString']]:
        if not match:
            return None
        return (
            self[:match.start(group)],
            self[match.start(group):match.end(group)],
            self[match.end(group):]
        )

    def partition(self, sep: str) -> Tuple['PositionedString', 'PositionedString', 'PositionedString']:
        left, sep, last = self.content.partition(sep)
        left_split = len(left)
        right_split = left_split + len(sep)
        return (
            self[:left_split],
            self[left_split:right_split],
            self[right_split:]
        )

    def split(self, sep: str) -> List['PositionedString']:
        start = 0
        result: List['PositionedString'] = []
        for part in self.content.split(sep):
            result.append(self[start:start+len(part)])
            start += len(part) + len(sep)
        return result
