import json
import logging
from pathlib import Path
from .config import STATE_FILE, DEFAULT_TIMEZONE


_state = None


def load_state():
    """Load bot state from a JSON file."""
    global _state
    if _state is not None:
        return _state
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            _state = json.load(f)
    except FileNotFoundError:
        logging.info("Creating new state file")
        _state = {
            "sent_links": [],
            "pending": {},
            "timezone": DEFAULT_TIMEZONE,
        }
    except json.JSONDecodeError as e:
        logging.error("Failed to parse state file: %s", e)
        _state = {
            "sent_links": [],
            "pending": {},
            "timezone": DEFAULT_TIMEZONE,
        }
    return _state


def save_state():
    """Persist state to disk."""
    if _state is None:
        return
    path = Path(STATE_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(_state, f, ensure_ascii=False, indent=2)


__all__ = ["load_state", "save_state", "_state"]
