#!/usr/bin/env python3

from typing import Tuple, Optional

import regex

from library.positioned import PositionedString


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
