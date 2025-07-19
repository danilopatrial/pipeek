# pipeek/src.py
# Main steam-search engine

from __future__ import annotations

import subprocess
import os
import json
import gzip
import bz2
import lzma
import sys
import io
import collections
import warnings
import time
import logging
import typing as t

from pathlib import Path

from . import const_def as c

try:
    import colorama
    colorama.init()

except ImportError:
    colorama = None
    warnings.warn(c.COLORAMA_IMPORT_WARN, category=UserWarning)

if t.TYPE_CHECKING:
    from _typeshed import SupportsWrite


class PipeekMatch(t.NamedTuple):
    match_value: bytes  # needle
    absolute_position: int
    left_context: bytes
    right_context: bytes
    elapsed_time: float


def echo_match(  # same as a __str__ method for PipeekMatch cls.
    match: PipeekMatch,
    file: "t.Optional[SupportsWrite[str]]" = None,
    flush: bool = False,
    log: bool = True,  # log at user config dir.
    ) -> None:

    """Prints the match to a stream or to sys.stdout by default"""

    left_context: str = match.left_context.decode(errors="replace")
    right_context: str = match.right_context.decode(errors="replace")
    match_value: str = match.match_value.decode(errors="replace")

    absolute_position: str = f"{match.absolute_position:,}"
    elapsed_time: str = f"{match.elapsed_time:,.6f}s"

    raw_info: str = f"pos: {absolute_position} · elapsed: {elapsed_time}"

    if colorama and os.isatty(1):
        match_value: str = f"{c.CYAN}{c.BOLD}{match_value}{c.RESET}"
        raw_info: str = f"{c.DIM} {raw_info}{c.RESET}"

    file: "SupportsWrite[str]" = sys.stdout if not file else file

    file.write(f"{left_context}{match_value}{right_context} {raw_info}")

    if log: logging.info(match)
    if flush: file.flush()


