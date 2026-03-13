from __future__ import annotations

from typing import Any, Mapping, Sequence

from transit_shared.settings_schema import SettingsError


def get_section(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    section = data.get(key)
    if not isinstance(section, Mapping):
        raise SettingsError(f"Missing or invalid [{key}] section")
    return section


def get_required(data: Mapping[str, Any], key: str) -> Any:
    if key not in data:
        raise SettingsError(f"Missing required settings key: {key}")
    return data[key]


def as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise SettingsError(f"{name} must be a boolean")


def as_int(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise SettingsError(f"{name} must be an integer")
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"{name} must be an integer") from exc
    return out


def as_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise SettingsError(f"{name} must be a number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise SettingsError(f"{name} must be a number") from exc
    return out


def as_str(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise SettingsError(f"{name} must be a string")
    out = value.strip()
    if not out:
        raise SettingsError(f"{name} must not be empty")
    return out


def as_float_tuple(value: Any, name: str, size: int) -> tuple[float, ...]:
    if not isinstance(value, Sequence):
        raise SettingsError(f"{name} must be an array of numbers")
    if len(value) != size:
        raise SettingsError(f"{name} must have {size} values")
    return tuple(as_float(v, name) for v in value)
