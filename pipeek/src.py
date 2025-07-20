# pipeek/src.py
# Main steam-search engine

from __future__ import annotations

import subprocess
import hashlib
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
import typing as t

from pathlib import Path

if __name__ == "__main__":
    import const_def as c
else:
    from . import const_def as c

try:
    import colorama

    colorama.init()

except ImportError:
    colorama = None
    warnings.warn(c.COLORAMA_IMPORT_WARN, category=UserWarning)

if t.TYPE_CHECKING:
    import _typeshed as _t


__ABSOLUTE_TIME_STAMP: float = time.time()


class __ConfAccess(object):
    def __init__(self) -> None:
        with open(c.JSON_CONFIG_PATH, "r", encoding="utf-8") as file:
            self._conf_dict: dict = json.load(file)

        for key, value in self._conf_dict.items():
            object.__setattr__(self, key, value)

    def __call__(self) -> dict:
        return self._conf_dict

    def restore(self) -> None:
        with open(c.JSON_CONFIG_PATH, "w") as file:
            json.dump(c.STANDARD_CONFIG, file, indent=4)
        self.__init__()

    def set(self, name: str, value: t.Any) -> None:
        if name not in self._conf_dict:
            raise KeyError(f"{name} is not a valid name.")

        self._conf_dict["name"] = value
        with open(c.JSON_CONFIG_PATH, "w") as file:
            json.dump(self._conf_dict, file, indent=4)

        self.__init__()


conf: __ConfAccess = __ConfAccess()


class PipeekMatch(t.NamedTuple):
    match_value: t.AnyStr  # needle
    absolute_position: int
    left_context: t.AnyStr
    right_context: t.AnyStr
    elapsed_time: float


def _convert_buffer_size(buffer_size: str = "8M") -> int:
    suffix: str = buffer_size[-1].upper()
    mul: dict = {"K": 1024, "M": 1024**2, "G": 1024**3}.get(suffix, 1)
    return int(buffer_size[:-1]) * mul if suffix in "KMG" else int(buffer_size)


def check_sum(
    stream: io.BufferedReader, hexdigested_hash: str, name: str = "md5"
) -> bool:

    hash = hashlib.new(name)  # hashlib._HashObject

    for chunk in stream.read(8_388_608):
        hash.update(chunk)

    return hash.hexdigest() == hexdigested_hash


def echo_match(  # same as a __str__ method for PipeekMatch cls.
    match: PipeekMatch,
    file: "t.Optional[_t.SupportsWrite[str]]" = None,
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

    file: "_t.SupportsWrite[str]" = sys.stdout if not file else file

    file.write(f"{left_context}{match_value}{right_context} {raw_info}\n")

    if log:
        logging.info(match)
    if flush:
        file.flush()


def open_stream(
    file: "_t.FileDescriptorOrPath", /, *, force_gzip: bool = False
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


def iter_needles_idx(needle: t.AnyStr, haystack: t.AnyStr) -> t.Iterator[int]:
    """Iterator of indices where needle occurs."""

    index: int = haystack.find(needle)

    while index != -1:
        yield index
        index = haystack.find(needle, index + 1)


def scan_stream(
    stream: io.BufferedReader,
    pattern: bytes,
    around_context: int = 10,
    buffer_size: int = 8_388_608,
) -> t.Iterator[PipeekMatch]:
    """Iterator of Matches of a given pattern on a given stram."""

    tail: bytes = b""
    position: int = -1
    len_pattern: int = len(pattern)

    while chunk := stream.read(buffer_size):
        chunk: bytes = tail + chunk

        for index in iter_needles_idx(pattern, chunk):
            absolute_position: int = position + index
            left_context: bytes = chunk[max(0, index - around_context) : index]
            right_context: bytes = chunk[
                index + len_pattern : index + len_pattern + around_context
            ]

            yield PipeekMatch(
                pattern,
                absolute_position,
                left_context,
                right_context,
                time.time() - __ABSOLUTE_TIME_STAMP
            )

        tail = chunk[-(around_context + len_pattern) :]
        position += len(chunk) - len(tail)


def peek_needle(
    needle: t.AnyStr,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    force_gzip: bool = False,
) -> t.NoReturn:
    """
    Find needle in a haystack (haystack beeing a `GenericPath` not a `AnyStr`)

    *NOTE: This function is not meant to be imported. Its CLI use only.
    And because of this will exit the code after running. Here is a simplified
    implementation of it:*
    ```
    >>> for file_obj in pipeek.walk("your/database/path/here"):
    >>>     with pipeek.open_stream(file_obj) as file:
    >>>         for match in pipeek.scan_stream(file, b"31415"):
    >>>             echo_match(match)
    ```
    """

    if isinstance(needle, str):
        needle: bytes = needle.encode()

    haystack = conf.haystack_path if not haystack else haystack
    buffer_size: int = _convert_buffer_size(conf.buffer_size)
    hit: bool = False  # register non-zero exit code, if False

    def _handler(filepath: Path) -> None:
        file_base_name: str = os.path.basename(filepath)

        with open_stream(filepath, force_gzip=force_gzip) as file:
            for i, match in enumerate(
                scan_stream(file, needle, conf.around_context, buffer_size)
            ):
                echo_match(match)
                logging.info(f'filename="{file_base_name}"; {match}')

                nonlocal hit
                hit = True  # successful exit

                if conf.max_matches != 0 and (i + 1 >= conf.max_matches):
                    sys.exit(0 if hit else 1)

    for file in walk(haystack):
        _handler(file)

    sys.exit(0 if hit else 1)


def peek_at(
    index: int,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    length: int = 10,
    force_gzip: bool = False,
) -> t.NoReturn:
    """
    Find needle at a given index.  

    *NOTE: This function is not meant to be imported. Its CLI use only.
    And because of this will exit the code after running. Here is a simplified
    implementation of it:*
    ```
    >>> for file_obj in pipeek.walk("your/database/path/here"):
    >>>     with pipeek.open_stream(file_obj) as file:
    >>>         file.seek(index - around_context)
    >>>         print(file.read(length + 2 * around_context))
    ```
    """

    haystack = conf.haystack_path if not haystack else haystack
    hit: bool = False  # register non-zero exit code, if False

    def _handler(filepath: Path) -> None:
        file_base_name: str = os.path.basename(filepath)

        with open_stream(filepath, force_gzip=force_gzip) as file:
            file.seek(index - conf.around_context)
            chunk: bytes = file.read(length + 2 * conf.around_context)

            offset = max(0, conf.around_context)
            left_context: bytes = chunk[:offset]
            needle: bytes = chunk[offset : offset + length]
            right_context: bytes = chunk[offset + length:]

            elapsed: float = time.time() - __ABSOLUTE_TIME_STAMP
            match: PipeekMatch = PipeekMatch(
                needle, index, left_context, right_context, elapsed,
            )

            nonlocal hit
            hit = True

            echo_match(match)
            logging.info(f"filename=\"{file_base_name}\"; {match}")

    for file in walk(haystack):
        _handler(file)

    sys.exit(0 if hit else 1)


def peek_twofold(
    substring_length: int,
    prefix_length: int,
    skip_bytes: int = 2,
    haystack: "t.Optional[_t.GenericPath[t.AnyStr]]" = None,
    force_gzip: bool = False,
) -> t.NoReturn:

    # TODO: better docs
    """
    Search duplicates.

    peek_twofold(n) is the first n-digit substring to repeat in a given haystack.
    """

    prefixes: list = [  # [b"01", b"02", ...]
        str(i).zfill(prefix_length).encode()
        for i in range(10 ** prefix_length)
    ]

    colisions: dict = {}

    def _handler(filepath: Path, prefix: bytes) -> None:
        file_base_name: str = os.path.basename(filepath)
        index: int = 0

        with open_stream(filepath, force_gzip=force_gzip) as file:
            skip = file.read(skip_bytes)

            # TODO: read with buffer limited size
            mm: mmap.mmap = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)

            for i in range(len(mm) - substring_length + 1):
                window: bytes = mm[i:i + substring_length]

                index += 1

                if not window.startswith(prefix):
                    continue

                r: int = colisions.get(window, -1)

                if r == -1:
                    colisions.update({window: index})
                    if (i := len(colisions)) % 500 == 0:
                        # TODO: fix this to show memory usage
                        print(f"Colisions len = {i}", end="\r", flush=True)
                else:
                    print(f"{file_base_name} - {prefix=} - Colision found at {index=} and index={colisions[window]} - Seq1={window}")

        colisions.clear()

    haystack = conf.haystack_path if not haystack else haystack

    for file in walk(haystack):
        for prefix in prefixes:
            # TODO: Better ui
            print(f"Serach at {os.path.basename(file)} - {prefix=}")
            _handler(file, prefix)

    sys.exit(0)