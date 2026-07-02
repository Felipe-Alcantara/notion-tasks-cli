"""Entrada para ``python -m cli``."""

from __future__ import annotations

from .notion_tasks import main

if __name__ == "__main__":
    raise SystemExit(main())
