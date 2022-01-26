#!/usr/bin/env python3

from typing import Optional
import logging
import json

from crossref.restful import Works, Etiquette
from fuzzywuzzy import fuzz

from .resources import get_resource

with open(get_resource("config.json")) as config_file:
    try:
        FUZZY_THRESHOLD: int = json.load(config_file).get(
            "fuzzy_matching_threshold", 97
        )
    except json.JSONDecodeError:
        FUZZY_THRESHOLD = 97


def load_etiquette_email() -> Optional[str]:
    try:
        with open(get_resource("crossref_etiquette_email.txt")) as email_file:
            email = email_file.readline().strip()
    except FileNotFoundError:
        return None
    if "@" in email:
        return email
    else:
        return None


PROJECT_NAME: str = "reference_formatter"
PROJECT_VERSION: str = "0.1.0"
PROJECT_URL: str = "https://github.com/iTaxoTools"
ETIQUETTE_EMAIL: Optional[str] = load_etiquette_email()

if ETIQUETTE_EMAIL:
    ETIQUETTE: Optional[Etiquette] = Etiquette(
        PROJECT_NAME, PROJECT_VERSION, PROJECT_URL, ETIQUETTE_EMAIL
    )
else:
    ETIQUETTE = None


def doi_from_title(title: str, fuzzy: bool) -> Optional[str]:
    if ETIQUETTE:
        endpoint = Works(etiquette=ETIQUETTE)
    else:
        endpoint = Works()
    try:
        request = (
            endpoint.query(title).select("DOI", "title").sort("relevance").order("desc")
        )
        logging.debug(f"Request {request.url}")
        response = next(request.__iter__())
        logging.debug(f"Got responce {response}")
    except StopIteration:
        return None
    except AttributeError:
        return None
    try:
        if match_title(response["title"][0], title, fuzzy):
            return "doi:" + response["DOI"]
        else:
            return None
    except IndexError:
        return None


def match_title(title1: str, title2: str, fuzzy: bool) -> bool:
    if not fuzzy:
        return title1.casefold() == title2.casefold()
    return fuzz.ratio(title1, title2) >= FUZZY_THRESHOLD
