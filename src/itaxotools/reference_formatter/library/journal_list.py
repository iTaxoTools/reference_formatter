#!/usr/bin/env python3

import sys
import os
from typing import Tuple, List, Dict, Optional
from enum import IntEnum

import pandas as pd
from ahocorasick_rs import AhoCorasick, MATCHKIND_LEFTMOST_LONGEST

from .utils import *
from .positioned import PositionedString
from .resources import get_resource


class NameForm(IntEnum):
    FullName = 0
    WithPeriods = 1
    Abbrev = 2
    WithPeriodsNoSpace = 3

    def __str__(self) -> str:
        return [
            "Full name",
            "Abbreviation with periods",
            "Abbreviation without periods",
            "Abbreviation without spaces",
        ][self]


N_NAME_FORMS = len(NameForm)


class JournalMatcher:
    def __init__(self) -> None:
        self.table, self.matcher = make_matcher(fill_missing(load()))

    def extract_journal(self, s: str) -> Optional[Tuple[Dict[NameForm, str], slice]]:
        matches = self.matcher.find_matches_as_indexes(s)
        if not matches:
            return None
        match_num, _, _ = matches[-1]
        journal_names = dict(self.table.iloc[match_num // N_NAME_FORMS])
        journal_name = journal_names[NameForm(match_num % N_NAME_FORMS)]
        start = s.index(journal_name)
        end = start + len(journal_name)
        return journal_names, slice(start, end)


def load() -> pd.DataFrame:
    path = get_resource("Journal_abbreviations.csv")

    return pd.read_table(path, dtype=str).rename(
        columns={
            "Full name accepted": NameForm.FullName,
            "Abbreviation with periods accepted": NameForm.WithPeriods,
            "Abbreviation without periods accepted": NameForm.Abbrev,
        }
    )


def fill_missing(table: pd.DataFrame) -> pd.DataFrame:
    table.dropna(how="all", inplace=True)
    table.fillna(axis=1, method="ffill", inplace=True)
    return table


def make_matcher(table: pd.DataFrame) -> Tuple[pd.DataFrame, AhoCorasick]:
    # normalize spaces
    table = table.applymap(normalize_space)
    # make sure there are spaces after every period in abbrev_period
    table[NameForm.WithPeriods] = table[NameForm.WithPeriods].str.replace(
        r"\.(?=\S)", ". "
    )
    # create column with for abbreviations with no spaces after the period
    table[NameForm.WithPeriodsNoSpace] = table[NameForm.WithPeriods].str.replace(
        r"\.\s", "."
    )
    # confirm columns order
    table = table[list(NameForm)]
    patterns: List[str] = []
    for _, row in table.iterrows():
        patterns.extend(row)
    return (table, AhoCorasick(patterns, matchkind=MATCHKIND_LEFTMOST_LONGEST))
