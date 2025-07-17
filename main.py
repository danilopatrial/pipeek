# pipeek/main.py

# MIT License
# 
# Copyright (c) 2025 Danilo Patrial
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import click
import subprocess
import os
import json
import platformdirs
import gzip
import bz2
import lzma
import sys
import io
import pathlib
import collections
import warnings
import time
import logging

import typing as t


try:
    import colorama

    colorama.init()

except (ImportError, NameError):
    colorama = None

    warnings.warn(
        "Colorama is not installed. Colored terminal output may not work properly.\n"
        "To fix this, install Colorama by running: pip install colorama\n"
        "Or install all dependencies using: pip install -r requirements.txt",
        category=UserWarning,
    )

from importlib.metadata import version, PackageNotFoundError


# --- Configuration File ------------------------------------------------------------------------------------


config_dir = platformdirs.user_config_dir("pipeek")
config_path = os.path.join(config_dir, "config.json")

os.makedirs(config_dir, exist_ok=True)

base_config: dict = {"buffer_size": "8M", "max_matches": 0, "around_context": 10}


# --- Logging -----------------------------------------------------------------------------------------------


logging.basicConfig(
    filename=os.path.join(config_dir, "pipeek.log"),
    filemode="w",
    format="%(asctime)s - %(message)s",
    level=logging.DEBUG,
)


# --- Utilities ---------------------------------------------------------------------------------------------


CYAN: str = "\033[36m"
BOLD: str = "\033[1m"
RESET: str = "\033[0m"
DIM: str = "\033[2m"


Match = collections.namedtuple("Match", "position left_context right_context")


def _access_config() -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _render_match(match: Match, needle: bytes, time: float) -> str:
    left: str = match.left_context.decode(errors="replace")
    right: str = match.right_context.decode(errors="replace")
    mid: str = needle.decode()

    if colorama and os.isatty(1):
        mid = f"{CYAN}{BOLD}{mid}{RESET}"

    line1 = f"{left}{mid}{right}"

    pos_txt = f"{match.position:,}"
    time_txt = f"{time:,.6f}s"

    line2 = f"pos: {pos_txt} │ elapsed: {time_txt}"

    if colorama:
        line2 = f"{DIM} {line2}{RESET}"

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


# --- Steam-Search Engine -----------------------------------------------------------------------------------


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
            left_context: bytes = data[max(0, idx - around) : idx]
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
) -> t.NoReturn:

    config_info: dict = _access_config()
    start: float = time.time()

    needle: bytes = needle.encode()

    buffer_size: int = _parse_bytes(config_info["buffer_size"])
    arround_context: int = config_info["around_context"]
    max_matches: int = config_info["max_matches"]

    hit: bool = False

    def handler(filepath: str | pathlib.Path, force_gzip: bool) -> None:
        with open_stream(filepath, force_gzip=force_gzip) as file:
            for i, match in enumerate(
                scan_stream(file, needle, arround_context, buffer_size)
            ):
                elapsed: float = time.time() - start
                print(_render_match(match, needle, elapsed))
                logging.info(
                    f'filename="{os.path.basename(filepath)}"; {match}; {needle=}; {elapsed=}'
                )

                nonlocal hit
                hit = True

                if max_matches != 0 and (i + 1) >= max_matches:
                    sys.exit(0 if hit else 1)

    streams: list[pathlib.Path] = [pathlib.Path(p) for p in haystack]
    for path_obj in streams:
        if path_obj.is_dir():
            for dirpath, _, filenames in os.walk(path_obj):
                for filename in filenames:
                    handler(pathlib.Path(dirpath) / filename, force_gzip)
        else:
            handler(path_obj, force_gzip)

    sys.exit(0 if hit else 1)


# --- Command Line Interface --------------------------------------------------------------------------------


def pkg_version() -> str:
    try:
        current_version: str = version("apollo")
    except PackageNotFoundError:
        current_version: str = "uknown"

    return current_version


@click.group()
@click.version_option(pkg_version(), prog_name="pipeek")
def cli() -> None:
    """Pipeek a fast, stream-based CLI, for searching digit
    patterns inside large text or compressed files."""
    pass


@cli.command()
@click.option(
    "-e",
    "editor",
    default="nvim",
    show_default=True,
    help="Editor to use (overrides $EDITOR env variable).",
)
@click.option(
    "--restore",
    is_flag=True,
    default=False,
    help="Restore default configuraion values.",
)
def conf(editor: str, restore: bool) -> None:
    """Open the config file on NVim, or on a specified editor."""

    if not os.path.exists(config_path) or restore:
        with open(config_path, "w") as f:
            json.dump(base_config, f, indent=4)

    # Determine the editor priority: CLI > ENV > default
    chosen_editor = editor or os.environ.get("EDITOR", "nvim")

    try:
        subprocess.run([chosen_editor, config_path])

    except FileNotFoundError:
        click.echo(f'"{chosen_editor}" not found. Falling back to Notepad...')
        subprocess.run(["notepad", config_path])


@cli.command()
@click.argument("needle")
@click.argument("haystack", nargs=-1, type=click.Path(exists=True), required=False)
@click.option(
    "-f",
    "--force-gzip",
    "force_gzip",
    is_flag=True,
    default=False,
    help="Force gunzip read",
)
def needle(needle: str, haystack: str, force_gzip: bool) -> None:
    peek_needle(needle, haystack, force_gzip)
