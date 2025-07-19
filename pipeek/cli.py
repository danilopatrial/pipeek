# pipeek/cli.py
# Command Line Interface

from __future__ import annotations

from importlib.metadata import version, PackageNotFoundError

import click
import os
import subprocess
import json

from . import const_def as c

from .src import peek_needle, peek_at

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


@cli.command()
@click.option("-e", "editor", default="nvim", show_default=True, help="Editor to use (overrides $EDITOR env variable).")
@click.option("--restore", is_flag=True, default=False, help="Restore default configuraion values.")
def conf(editor: str, restore: bool) -> None:
    """Open the config file on NVim, or on a specified editor."""

    if not os.path.exists(c.JSON_CONFIG_PATH) or restore:
        with open(c.JSON_CONFIG_PATH, "w") as f:
            json.dump(c.STANDARD_CONFIG, f, indent=4)

    # Determine the editor priority: CLI > ENV > default
    chosen_editor = editor or os.environ.get("EDITOR", "nvim")

    try:
        subprocess.run([chosen_editor, c.JSON_CONFIG_PATH])

    except FileNotFoundError:
        click.echo(f'"{chosen_editor}" not found. Falling back to Notepad...')
        subprocess.run(["notepad", c.JSON_CONFIG_PATH])


@cli.command()
@click.argument("needle")
@click.argument("haystack", nargs=-1, type=click.Path(exists=True), required=False, default=None)
@click.option("-f", "--force-gzip", "force_gzip", is_flag=True, default=False, help="Force gunzip read")
def needle(needle: str, haystack: str | None, force_gzip: bool) -> None:
    """Find a needle in a haystack"""
    peek_needle(needle, haystack, force_gzip)


@cli.command()
@click.argument("index", type=int)
@click.argument("haystack", nargs=-1, type=click.Path(exists=True), required=False, default=None)
@click.option("--len", "len", type=int, default=10)
@click.option("-f", "--force-gzip", "force_gzip", is_flag=True, default=False, help="Force gunzip read")
def at(index: int, haystack: str | None, len: int, force_gzip: bool) -> None:
    """Peek at a given index."""
    peek_at(index, haystack, len, force_gzip)