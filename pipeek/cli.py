# pipeek/cli.py
# Main command line interface

from __future__ import annotations

import click

from . import main as pipeek

@click.group(invoke_without_command=True)
@click.argument("pattern")
@click.argument("files", nargs=-1, type=click.Path(exists=True), required=False)
@click.option("--around", default=20, show_default=True)
@click.option("-m", "--max-matches", type=int, default=0)
@click.option("--fmt", type=click.Choice(["color", "plain"]), default="color")
@click.option("-b", "--buffer-size", type=str, default="8M", help="1K/1M/1G suffixes ok")
@click.option("-z", "--gzip", "force_gzip", is_flag=True, help="Force gunzip read")
def cli(pattern, files, around, fmt, max_matches, buffer_size, force_gzip):

    pipeek._set_config("around_context", around)
    pipeek._set_config("max_matches", max_matches)
    pipeek._set_config("buffer_size", pipeek._parse_bytes(buffer_size))

    pipeek.peek_needle(pattern, files, force_gzip, fmt)