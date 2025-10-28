import os

from mtcli.conf import config

SYMBOL = os.getenv("SYMBOL", config["DEFAULT"].get("symbol", fallback="WIN$N"))
DAYS_AVERAGE = int(
    os.getenv("DAYS_AVERAGE", config["DEFAULT"].getint("days_average", fallback=5))
)
VOLUME = os.getenv("VOLUME", config["DEFAULT"].get("volume", fallback="tick"))
TIMEZONE = os.getenv(
    "TIMEZONE", config["DEFAULT"].get("timezone", fallback="America/Sao_Paulo")
)
