#!/usr/bin/env python3

from typing import NamedTuple, Optional, Union


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
        return PositionedString(content=s, start=start, end=end)

    def __len__(self) -> int:
        return len(self.content)

    def __getitem__(self, index: Union[int, slice]) -> PositionedString:
        if isinstance(index, int):
            return PositionedString(self.content[index], index, index + 1)
        elif isinstance(index, slice):
            start, end, stride = index.indices(len(self))
            if stride != 1:
                raise IndexError("stride is not 1")
            return PositionedString(self.content[start:end],
                                    self.start + start,
                                    self.start + end)
        else:
            raise TypeError
