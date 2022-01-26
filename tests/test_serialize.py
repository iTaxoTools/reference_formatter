#!/usr/bin/env python3

from typing import Iterator
from pathlib import Path

import pytest

from itaxotools.reference_formatter.library.citation import txt_to_references, Reference
from itaxotools.reference_formatter.library.options import default_options
from itaxotools.reference_formatter.library.journal_list import JournalMatcher

JOURNAL_MATCHER = JournalMatcher()


def references() -> Iterator[Reference]:
    testfile_path = Path(__file__).with_name("Referencelist2.txt")
    with open(testfile_path) as testfile:
        for ref in txt_to_references(testfile, default_options(), JOURNAL_MATCHER):
            if isinstance(ref, Reference):
                yield ref


@pytest.mark.parametrize("ref", references())
def test_serialize(ref: Reference) -> None:
    ref_serialized = ref.serialize("{}")
    ref_deserialized = ref.deserialize(ref_serialized, "{}", JOURNAL_MATCHER)
    assert ref_deserialized == ref
