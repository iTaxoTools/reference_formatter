#!/usr/bin/env python3

import regex


def normalize_space(s: str) -> str:
    """
    Collapses whitespace sequences and removes spaces before some punctuation
    """
    s = regex.sub(r"\s{2,}", " ", s)
    s = regex.sub(r"[\u00A0\u202F ](?=[.,;:])", "", s)
    return s


def replace_slice(input: str, position: slice, replacement: str) -> str:
    start, stop, step = position.indices(len(input))
    if step != 1:
        raise ValueError(f"{position} does not define a string part")
    return input[:start] + replacement + input[stop:]
