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
import click
import os
import colorama
import time

import typing as t


colorama.init()


__all__: list = []


# +--- UTILS --------------------------------------------------------------------------------+

Match = collections.namedtuple("Match", "position leftCTX rightCTX")


def _iterNeedlesIdxs(haystack: bytes, needle: bytes, /) -> t.Iterator[int]:
    """Generator of indices where needle occurs"""
    start: int = 0
    while True:
        i: int = haystack.find(needle, start)
        if i == -1: return
        yield i
        start = i + 1


def _parseBytes(string: str) -> int:
    suffix: str = string[-1].upper()
    mul: dict = {"K": 1024, "M": 1024**2, "G": 1024**3}.get(suffix, 1)
    return int(string[:-1]) * mul if suffix in "KMG" else int(string)


CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def _renderMatch(match: Match, needle: bytes, mode: str, time: float) -> str:
    left  : str = match.leftCTX.decode(errors="replace")
    right : str = match.rightCTX.decode(errors="replace")
    mid   : str = needle.decode()

    if mode == "color" and os.isatty(1):
        mid = f"{CYAN}{BOLD}{mid}{RESET}"

    line1 = f"{left}{mid}{right}"

    pos_txt  = f"{match.position:,}"
    time_txt = f"{time:,.6f}s"
    line2 = f"{DIM} pos: {pos_txt} │ elapsed: {time_txt}{RESET}"

    return f"{line1} {line2}"


# +--- MAIN ---------------------------------------------------------------------------------+


def openStream(
    filepath: str | pathlib.Path, forceGzip: bool = False
) -> io.BufferedReader:
    """Return a binary buffered stream for txt or compressed files."""

    path: pathlib.Path = pathlib.Path(filepath)

    if path == pathlib.Path("-"):  # stdin support
        return sys.stdin.buffer

    ext: str = path.suffix.lower()

    if forceGzip or ext == ".gz":
        return gzip.open(path, "rb")

    if ext in (".bz2", ".bz"):
        return bz2.open(path, "rb")

    if ext in (".xz", ".lzma"):
        return lzma.open(path, "rb")

    return path.open("rb")


def scanSteam(
    stream: io.BufferedReader,
    pattern: bytes,
    around: int = 20,
    bufferSize: int = 8_388_608,
) -> t.Iterator[Match]:

    tail: bytes = b""
    position: int = -1

    decFilter = bytes.maketrans(b"", b"")
    deleteChars = b".\n\r "

    while chunk := stream.read(bufferSize):
        chunk: bytes = tail + chunk
        data: bytes = chunk.translate(decFilter, deleteChars)

        for idx in _iterNeedlesIdxs(data, pattern):

            absolutePosition: int = position + idx + 1
            left: bytes = data[max(0, idx - around): idx]
            right: bytes = data[idx + len(pattern): idx + len(pattern) + around]

            yield Match(absolutePosition, left, right)

        position += len(data)
        tail = data[-(around + len(pattern)):]


# +--- COMMAND LINE INTERFACE ---------------------------------------------------------------+


@click.group(invoke_without_command=True)
@click.argument("pattern")
@click.argument("files", nargs=-1, type=click.Path(exists=True), required=False)
@click.option("--around", default=20, show_default=True)
@click.option("-m", "--max-matches", type=int, default=None)
@click.option("--fmt", type=click.Choice(["color", "plain"]), default="color")
@click.option("-b", "--buffer-size", type=str, default="8M", help="1K/1M/1G suffixes ok")
@click.option("-z", "--gzip", "force_gzip", is_flag=True, help="Force gunzip read")
def cli(pattern, files, around, fmt, max_matches, buffer_size, force_gzip):
    needle: bytes = pattern.encode()
    bufferSize: int = _parseBytes(buffer_size)
    hit: bool = False
    streams: list = [("-", )] if not files else files

    start = time.time()

    for filepath in streams:
        with openStream(filepath, forceGzip=force_gzip) as file:
            for n, m in enumerate(scanSteam(file, needle, around, bufferSize)):
                print(_renderMatch(m, needle, fmt, time.time() - start))
                hit = True
                if max_matches and (n + 1) >= max_matches:
                    sys.exit(0 if hit else 1)

    sys.exit(0 if hit else 1)