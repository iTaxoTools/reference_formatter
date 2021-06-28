#!/usr/bin/env python3

import sys
import os
from typing import Tuple, List, Dict, Optional
from enum import Enum

import pandas as pd
from ahocorasick_rs import AhoCorasick, MATCHKIND_LEFTMOST_LONGEST

from library.utils import *

resource_path = getattr(sys, "_MEIPASS", sys.path[0])


class NameForm(Enum):
    FullName = 0
    WithPeriods = 1
    Abbrev = 2
    WithPeriodsNoSpace = 3


N_NAME_FORMS = len(NameForm)


class JournalMatcher:
    def __init__(self) -> None:
        self.table, self.matcher = make_matcher(fill_missing(load()))

    def extract_journal(self, s: str) -> Tuple[str, Optional[Dict[NameForm, str]], str]:
        matches = self.matcher.find_matches_as_indexes(s)
        if not matches:
            return (s, None, "")
        match_num, _, _ = matches[-1]
        journal_names = dict(self.table.iloc[match_num // N_NAME_FORMS])
        journal_name = journal_names[NameForm(match_num % N_NAME_FORMS)]
        prefix, _, suffix = s.partition(journal_name)
        return prefix, journal_names, suffix


def load() -> pd.DataFrame:
    path = os.path.join(resource_path, "data", "Journal_abbreviations.csv")

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
