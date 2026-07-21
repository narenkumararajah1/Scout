"""Shared JSON-list serialization helper for repositories storing a list
field (e.g. supporting_signal_ids, preferred_channels) as SQLite TEXT.
"""

import json


def dump_list(values: list[str]) -> str:
    return json.dumps(values)


def load_list(raw: str) -> list[str]:
    return json.loads(raw)
