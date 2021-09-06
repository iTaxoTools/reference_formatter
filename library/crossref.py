#!/usr/bin/env python3

from typing import Optional
import logging

from crossref.restful import Works, Etiquette

from library.resources import get_resource


def load_etiquette_email() -> Optional[str]:
    try:
        with open(get_resource("crossref_etiquette_email.txt")) as email_file:
            email = email_file.readline().strip()
    except FileNotFoundError:
        return None
    if '@' in email:
        return email
    else:
        return None


PROJECT_NAME: str = 'reference-formatter'
PROJECT_VERSION: str = '0.1.0'
PROJECT_URL: str = 'https://github.com/iTaxoTools'
ETIQUETTE_EMAIL: Optional[str] = load_etiquette_email()

if ETIQUETTE_EMAIL:
    ETIQUETTE: Optional[Etiquette] = Etiquette(
        PROJECT_NAME, PROJECT_VERSION, PROJECT_URL, ETIQUETTE_EMAIL)
else:
    ETIQUETTE = None


def doi_from_title(title: str) -> Optional[str]:
    if ETIQUETTE:
        endpoint = Works(etiquette=ETIQUETTE)
    else:
        endpoint = Works()
    try:
        request = (endpoint.query(title).select(
            'DOI', 'title').sort('relevance').order('desc'))
        logging.debug(f"Request {request.url}")
        response = next(request.__iter__())
        logging.debug(f"Got responce {response}")
    except StopIteration:
        return None
    except AttributeError:
        return None
    try:
        if response['title'][0].casefold() == title.casefold():
            return response['DOI']
        else:
            return None
    except IndexError:
        return None
