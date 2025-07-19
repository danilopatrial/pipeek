import logging
import os

from . import const_def as c
from .cli import cli as main

if __name__ == "__main__":

    # config directory tied to the user
    os.makedirs(c.CONFIG_DIR, exist_ok=True)

    logging.basicConfig(
        filename=c.JSON_CONFIG_PATH,
        filemode="w",
        format="%(asctime)s - %(message)s",
        level=logging.DEBUG,
    )

    main()
