from __future__ import annotations

BUS_ROUTE_TYPES = frozenset(
    {
        "3",
        "700",
        "701",
        "702",
        "703",
        "704",
        "705",
        "706",
        "707",
        "708",
        "709",
        "710",
        "711",
        "712",
        "713",
        "714",
        "715",
        "716",
    }
)


def is_bus_route_type(route_type: str) -> bool:
    return str(route_type).strip() in BUS_ROUTE_TYPES


def is_rail_like_route_type(route_type: str) -> bool:
    normalized = str(route_type).strip()
    return bool(normalized) and normalized not in BUS_ROUTE_TYPES
