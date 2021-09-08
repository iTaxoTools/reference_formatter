#!/usr/bin/env python3

from typing import Any
from pathlib import Path
import sys
# import importlib.resources

# _resource_path = importlib.resources.files('itaxotools.concatenator') / "resources"
_resource_path = Path(sys.path[0]) / "data"


def get_resource(path: Any) -> str:
    return str(_resource_path / path)
