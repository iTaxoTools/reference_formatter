#!/usr/bin/env python3

import sys
import os
import pandas as pd
import regex

resource_path = getattr(sys, "_MEIPASS", sys.path[0])


def load() -> pd.DataFrame:
    path = os.path.join(resource_path, "data", "Journal_abbreviations.csv")
    return pd.read_table(path, dtype=str)


def fill_missing(table: pd.DataFrame) -> pd.DataFrame:
    table.dropna(how="all", inplace=True)
    table.fillna(axis=1, method="ffill", inplace=True)
    return table


def make_regex(table: pd.DataFrame) -> regex.Pattern:
    table = table.applymap(lambda s: regex.escape(s, literal_spaces=True))
    table["Abbreviation with periods accepted"] = table[
        "Abbreviation with periods accepted"
    ].str.replace(r"\\\.\s*", r"\.\s*")
    column_regexes = [table[column].str.cat(None, sep="|") for column in table.columns]
    return regex.compile("|".join(column_regexes))
