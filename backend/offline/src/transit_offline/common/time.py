from __future__ import annotations


def parse_gtfs_time_to_seconds(value: str) -> int:
    """Parse GTFS HH:MM:SS, supporting HH >= 24."""
    if not value:
        raise ValueError("empty GTFS time")
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError(f"invalid GTFS time '{value}'")
    h, m, s = (int(parts[0]), int(parts[1]), int(parts[2]))
    if m < 0 or m >= 60 or s < 0 or s >= 60 or h < 0:
        raise ValueError(f"invalid GTFS time '{value}'")
    return h * 3600 + m * 60 + s
