#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import hashlib
import logging
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
import mmap
import psutil
import platformdirs
import click
import typing as t

from importlib.metadata import version, PackageNotFoundError
from pathlib import Path

if t.TYPE_CHECKING:
    import _typeshed as _t

_ColoramaImportWarn: str = (
    "Colorama is not installed. Colored terminal output may not work properly.\n"
    "To fix this, install Colorama by running: pip install colorama\n"
)

try:
    import colorama

    colorama.init()

except ImportError:
    colorama = None
    warnings.warn(_ColoramaImportWarn, category=UserWarning)


logging.basicConfig(
    filename=platformdirs.user_log_path("pipeek"),  # log path tied to the user
    format="[%(asctime)s - %(name)s:%(lineno)d - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


_AbsoluteTimeStamp: float = time.time()


class HashMismatchError(BaseException): ...


def check_sum(
    stream: io.BufferedReader,
    hexdigested_hash: t.AnyStr,
    name: str = "md5",
    raise_mismatch_error: bool = False,
) -> bool | t.Literal[True]:

    hash = hashlib.new(name)  # hashlib._HashObject

    for chunk in stream.read(8_388_608):
        hash.update(chunk)

    result: bool = hash.hexdigest() == str(hexdigested_hash)

    if raise_mismatch_error and result == False:
        e_msg: str = (
            f"Invalid hash sum compare: {hash.hexdigest()} != {hexdigested_hash}"
        )
        logging.exception(e_msg, exc_info=HashMismatchError)
        raise HashMismatchError(e_msg)

    return result


def open_stream(
    file: "_t.FileDescriptorOrPath", force_gzip: bool = False
) -> io.BufferedReader:
    """Return a binary buffered stram for txt or compressed files.
    Read bytes (`rb`) only."""

    path: Path = Path(file)

    if path == Path("-"):  # stdin support
        return sys.stdin.buffer

    ext: str = path.suffix.lower()

    if force_gzip or ext == ".gz":
        return gzip.open(path, "rb")

    if ext in (".bz2", ".bz"):
        return bz2.open(path, "rb")

    if ext in (".xz", ".lzma"):
        return lzma.open(path, "rb")

    return path.open("rb")


def walk(*roots: "_t.GenericPath[t.AnyStr]") -> t.Iterator[Path]:
    """Directory tree generator. Same as `os.walk` but works
    for numerous roots and yields as a `pathlib.Path` object.
    Also accepts *not-a-directory* generic paths."""

    paths: set[Path] = {Path(p) for p in roots}

    for path in paths:

        if not path.is_dir():
            yield path
            continue

        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                yield (Path(dirpath) / filename)


def peek_duplicate(
    substring_length: int,
    prefix_length: int,
    skip_bytes: int = 2,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    num_matches: int = -1,
    force_gzip: bool = False,
) -> t.NoReturn: ...


def peek_needle(
    needle: t.AnyStr,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    num_matches: int = -1,
    force_gzip: bool = False,
) -> t.NoReturn: ...


def peek_at(
    index: int,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    length: int = 10,
    force_gzip: bool = False,
) -> t.NoReturn: ...


# Command Line Interface
# ``````````````````````

def pkg_version() -> str:
    try:
        current_version: str = version("pipeek")
    except PackageNotFoundError:
        current_version: str = "uknown"

    return current_version


@click.group()
@click.version_option(pkg_version(), prog_name="pipeek")
def cli() -> None:
    """Pipeek a fast, stream-based CLI, for searching digit
    patterns inside large text or compressed files."""
    pass