"""Copy tablet assets into Home Assistant's /local tree."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SOURCE_DIR = Path(__file__).parent / "www"


async def async_install_www(hass: HomeAssistant) -> None:
    dest_dir = Path(hass.config.path("www", "flightwall"))

    def _copy() -> None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in SOURCE_DIR.glob("*"):
            if src.is_file():
                (dest_dir / src.name).write_bytes(src.read_bytes())

    try:
        await hass.async_add_executor_job(_copy)
    except OSError as err:
        _LOGGER.debug("Could not install Flight Wall www files: %s", err)
