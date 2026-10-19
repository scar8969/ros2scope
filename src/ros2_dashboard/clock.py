"""Naive UTC timestamps.

The ``DateTime`` columns in this package are naive (no timezone), so the value
written into them must be naive as well. ``datetime.utcnow()`` produced exactly
that, but it is deprecated since Python 3.12 and removed in 3.14, and its
replacement ``datetime.now(UTC)`` is timezone-aware. Dropping the tzinfo keeps
the stored values byte-identical to what the old default wrote.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, matching the database columns."""
    return datetime.now(UTC).replace(tzinfo=None)
