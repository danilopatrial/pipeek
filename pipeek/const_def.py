# pipeek/const_def.py
# Useful constants and definitions

from __future__ import annotations

import platformdirs
import os


COLORAMA_IMPORT_WARN: str = (
    "Colorama is not installed. Colored terminal output may not work properly.\n"
    "To fix this, install Colorama by running: pip install colorama\n"
)

CONFIG_DIR: str = platformdirs.user_config_dir("pipeek")
JSON_CONFIG_PATH: str = os.path.join(CONFIG_DIR, "config.json")

CYAN: str = "\033[36m"
BOLD: str = "\033[1m"
RESET: str = "\033[0m"
DIM: str = "\033[2m"

STANDARD_CONFIG: dict = {
    "buffer_size": "8M",
    "max_matches": 0,
    "around_context": 10,
    "haystack_path": None,
}