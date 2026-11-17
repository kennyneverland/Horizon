"""Enable the per-source ``max_items`` limit that the config already declares.

``RSSSourceConfig`` has no ``max_items`` field, so pydantic drops the value at
validation time and ``RSSScraper`` falls back to the global cap of 8 for every
feed -- the per-source limits in ``data/config.github.json`` were dead settings
for as long as they existed (华尔街见闻 was configured at 6 and still yielded 8).

Rebuilding the model schema with ``extra="allow"`` makes the configured value
survive validation, which is all the scraper needs because it reads it with
``getattr``.

The real fix is one field on ``RSSSourceConfig`` in ``src/models.py``:

    max_items: Optional[int] = None

That file is 23 KB, above the connector's single-write limit, so the schema is
patched at import time instead. Delete this module and add the field once the
file can be written whole.
"""

from __future__ import annotations

import logging

from ..models import RSSSourceConfig

logger = logging.getLogger(__name__)


def enable_per_source_item_caps() -> None:
    """Rebuild ``RSSSourceConfig`` so extra keys such as ``max_items`` survive.

    A failed rebuild must not stop the run: the feeds simply keep the global
    cap, which is the behaviour that shipped before this module existed.
    """
    try:
        RSSSourceConfig.model_config["extra"] = "allow"
        RSSSourceConfig.model_rebuild(force=True)
    except Exception:  # noqa: BLE001 - degrade to the global cap, never crash
        logger.warning(
            "Could not enable per-source max_items; feeds use the global cap",
            exc_info=True,
        )


enable_per_source_item_caps()
