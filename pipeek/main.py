# pipeek/main.py
# Core steam-search engine

from __future__ import annotations

import gzip
import bz2
import lzma
import sys
import io
import pathlib
import collections
import os
import warnings
import time
import json
import logging

import typing as t


try:
    import colorama

    colorama.init()

except (ImportError, NameError):
    import warnings

    warnings.warn(
        "Colorama is not installed. Colored terminal output may not work properly.\n"
        "To fix this, install Colorama by running: pip install colorama\n"
        "Or install all dependencies using: pip install -r requirements.txt",
        category=UserWarning,
    )


logging.basicConfig(
    filename="pipeek.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)


CYAN: str = "\033[36m"
BOLD: str = "\033[1m"
RESET: str = "\033[0m"
DIM: str = "\033[2m"


@t.runtime_checkable
class SupportsWrite(t.Protocol):
    def write(self, __x) -> None: ...


Match = collections.namedtuple("Match", "position left_context right_context")


def _access_config() -> dict:
    with open("pipeek/pipeek/config.json", "r", encoding="utf-8") as file:
        return json.load(file)


def _set_config(attr: str, value: t.Any) -> None:
    current_dict: dict = _access_config()

    if not attr in current_dict:
        raise Exception(f"Invalid attribute: {attr=}")

    current_dict[attr] = value

    with open("pipeek/pipeek/config.json", "w", encoding="utf-8") as file:
        json.dump(current_dict, file, indent=4)


def _render_match(match: Match, needle: bytes, mode: str, time: float) -> str:
    left: str = match.left_context.decode(errors="replace")
    right: str = match.right_context.decode(errors="replace")
    mid: str = needle.decode()

    if mode == "color" and os.isatty(1):
        mid = f"{CYAN}{BOLD}{mid}{RESET}"

    line1 = f"{left}{mid}{right}"

    pos_txt = f"{match.position:,}"
    time_txt = f"{time:,.6f}s"
    line2 = f"{DIM} pos: {pos_txt} │ elapsed: {time_txt}{RESET}"

    return f"{line1} {line2}"


def _parse_bytes(memory_value: str, /) -> int:
    suffix: str = memory_value[-1].upper()
    mul: dict = {"K": 1024, "M": 1024**2, "G": 1024**3}.get(suffix, 1)
    return int(memory_value[:-1]) * mul if suffix in "KMG" else int(memory_value)


def _iter_needle_indexes(haystack: bytes, needle: bytes, /) -> t.Iterator[int]:
    """Iterator of indices where needle occurs."""
    start: int = 0
    while True:
        i: int = haystack.find(needle, start)
        if i == -1:
            return
        yield i
        start = i + 1


def open_stream(
    file: str | pathlib.Path, /, *, force_gzip: bool = False
) -> io.BufferedReader:
    """Return a binary buffered stram for txt or compressed files."""

    path: pathlib.Path = pathlib.Path(file)

    if path == pathlib.Path("-"):  # stdin support
        return sys.stdin.buffer

    ext: str = path.suffix.lower()

    if force_gzip or ext == ".gz":
        return gzip.open(path, "rb")

    if ext in (".bz2", ".bz"):
        return bz2.open(path, "rb")

    if ext in (".xz", ".lzma"):
        return lzma.open(path, "rb")

    return path.open("rb")


def scan_stream(
    stream: io.BufferedReader,
    pattern: bytes,
    around: int = 20,
    buffer_size: int = 8_388_608,
) -> t.Iterator[Match]:
    """Iterator of Matches of a given pattern on a given stram."""

    tail: bytes = b""
    position: int = -1

    dec_filter: bytes = bytes.maketrans(b"", b"")
    delete_chars: bytes = b".\n\r "

    while chunk := stream.read(buffer_size):
        chunk: bytes = tail + chunk
        data: bytes = chunk.translate(dec_filter, delete_chars)

        for idx in _iter_needle_indexes(data, pattern):

            absolute_position: int = position + idx + 1
            left_context: bytes = data[max(0, idx - around)]
            right_context: bytes = data[
                idx + len(pattern) : idx + len(pattern) + around
            ]

            yield Match(absolute_position, left_context, right_context)

        position += len(data)
        tail = data[-(around + len(pattern)) :]


def peek_needle(
    needle: str,
    haystack: str | pathlib.Path,
    force_gzip: bool = False,
    stdout_fmt: str = "color",
) -> t.NoReturn:

    config_info: dict = _access_config()
    start: float = time.time()

    needle: bytes = needle.encode()

    buffer_size: int = config_info["buffer_size"]
    arround_context: int = config_info["around_context"]
    max_matches: int = config_info["max_matches"]

    hit: bool = False

    def handler(filepath: str | pathlib.Path, force_gzip: bool) -> None:
        with open_stream(filepath, force_gzip=force_gzip) as file:
            for i, match in enumerate(
                scan_stream(file, needle, arround_context, buffer_size)
            ):
                elapsed: float = time.time() - start
                print(_render_match(match, needle, stdout_fmt, elapsed))
                logging.info(f"{match=} {needle=} {elapsed=}")

                nonlocal hit
                hit = True

                if max_matches != 0 and (i + 1) >= max_matches:
                    sys.exit(0 if hit else 1)

    streams: list[pathlib.Path] = [
        pathlib.Path(p) for p in haystack
    ]
    for path_obj in streams:
        if path_obj.is_dir():
            for dirpath, _, filenames in os.walk(path_obj):
                for filename in filenames:
                    handler(pathlib.Path(dirpath) / filename, force_gzip)
        else:
            handler(path_obj, force_gzip)

    sys.exit(0 if hit else 1)