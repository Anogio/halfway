from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from transit_backend.config.settings import get_city_artifacts_dir, load_backend_config
from transit_backend.core.artifacts import RuntimeData, load_runtime_data
from transit_backend.core.pathing import compute_path
from transit_backend.core.routing import build_spatial_index


@dataclass(frozen=True)
class OdPair:
    name: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float


EXTRA_ODS: dict[str, list[OdPair]] = {
    "paris": [
        OdPair(
            name="Republique to eastern suburb feeder",
            origin_lat=48.86823,
            origin_lon=2.35945,
            destination_lat=48.84565,
            destination_lon=2.50564,
        ),
        OdPair(
            name="Jacques Bonsergent to Barbes via Gare de l'Est",
            origin_lat=48.86826,
            origin_lon=2.35942,
            destination_lat=48.88479,
            destination_lon=2.34669,
        ),
        OdPair(
            name="Montparnasse to La Defense",
            origin_lat=48.8422,
            origin_lon=2.3215,
            destination_lat=48.8919,
            destination_lon=2.2384,
        ),
        OdPair(
            name="Belleville to Denfert-Rochereau",
            origin_lat=48.8720,
            origin_lon=2.3769,
            destination_lat=48.8338,
            destination_lon=2.3324,
        ),
    ],
    "london": [
        OdPair(
            name="Stondon Walk to Queen Victoria Street",
            origin_lat=51.53202,
            origin_lon=0.04584,
            destination_lat=51.51171,
            destination_lon=-0.09979,
        ),
        OdPair(
            name="Streatham High Road to Sarsfeld Road",
            origin_lat=51.42689,
            origin_lon=-0.13075,
            destination_lat=51.44189,
            destination_lon=-0.16132,
        ),
        OdPair(
            name="Nursery Road to Bowden Street",
            origin_lat=51.46357,
            origin_lon=-0.11688,
            destination_lat=51.48748,
            destination_lon=-0.11069,
        ),
        OdPair(
            name="Brixton to Oxford Circus",
            origin_lat=51.4627,
            origin_lon=-0.1145,
            destination_lat=51.5152,
            destination_lon=-0.1419,
        ),
    ],
}


def _validation_pairs(cfg: object, city: str) -> list[OdPair]:
    city_cfg = cfg.settings.cities[city]
    pairs: list[OdPair] = []
    for row in city_cfg.validation.od_pairs:
        pairs.append(
            OdPair(
                name=row.name,
                origin_lat=row.from_lat,
                origin_lon=row.from_lon,
                destination_lat=row.to_lat,
                destination_lon=row.to_lon,
            )
        )
    return pairs


def _dedupe_pairs(rows: Iterable[OdPair]) -> list[OdPair]:
    out: list[OdPair] = []
    seen: set[tuple[float, float, float, float]] = set()
    for row in rows:
        key = (
            round(row.origin_lat, 6),
            round(row.origin_lon, 6),
            round(row.destination_lat, 6),
            round(row.destination_lon, 6),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _segment_signature(path: dict[str, object]) -> list[str]:
    signature: list[str] = []
    for segment in path.get("segments", []):
        if not isinstance(segment, dict):
            continue
        kind = str(segment.get("kind", ""))
        if kind == "ride":
            signature.append(f"ride:{segment.get('route_label') or segment.get('route_id')}")
        elif kind.startswith("transfer"):
            signature.append("transfer")
        elif kind.startswith("walk"):
            signature.append(kind)
        else:
            signature.append(kind)
    return signature


def _transfer_count(path: dict[str, object]) -> int:
    count = 0
    for segment in path.get("segments", []):
        if isinstance(segment, dict) and str(segment.get("kind", "")).startswith("transfer"):
            count += 1
    return count


def _ride_labels(path: dict[str, object]) -> list[str]:
    labels: list[str] = []
    for segment in path.get("segments", []):
        if isinstance(segment, dict) and segment.get("kind") == "ride":
            labels.append(str(segment.get("route_label") or segment.get("route_id") or ""))
    return labels


def _summary(path: dict[str, object]) -> dict[str, object]:
    summary = path.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    return {
        "reachable": bool(path.get("reachable")),
        "total_time_s": int(summary.get("total_time_s", -1)),
        "origin_walk_s": int(summary.get("origin_walk_s", 0)),
        "graph_time_s": int(summary.get("graph_time_s", 0)),
        "boarding_wait_s": int(summary.get("boarding_wait_s", 0)),
        "ride_runtime_s": int(summary.get("ride_runtime_s", 0)),
        "transfer_s": int(summary.get("transfer_s", 0)),
        "destination_walk_s": int(summary.get("destination_walk_s", 0)),
        "transfer_count": _transfer_count(path),
        "ride_labels": _ride_labels(path),
        "segment_signature": _segment_signature(path),
    }


def _compute(
    runtime: RuntimeData,
    pair: OdPair,
    *,
    radius_m: float,
    fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
) -> dict[str, object]:
    spatial = build_spatial_index(runtime, radius_m=radius_m)
    path = compute_path(
        runtime,
        spatial,
        origin_lat=pair.origin_lat,
        origin_lon=pair.origin_lon,
        destination_lat=pair.destination_lat,
        destination_lon=pair.destination_lon,
        first_mile_radius_m=radius_m,
        first_mile_fallback_k=fallback_k,
        max_seed_nodes=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
        max_time_s=max_time_s,
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare v1 and v2 path outputs for curated OD pairs.")
    parser.add_argument("--city", required=True)
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    cfg = load_backend_config()
    city = args.city.strip()
    if city not in cfg.settings.cities:
        known = ", ".join(sorted(cfg.settings.cities))
        raise SystemExit(f"Unknown city '{city}'. Known cities: {known}")

    artifacts_dir = get_city_artifacts_dir(cfg, city)
    runtime_v1 = load_runtime_data(artifacts_dir, version="v1")
    runtime_v2 = load_runtime_data(artifacts_dir, version="v2")

    search = cfg.settings.search
    runtime_cfg = cfg.settings.runtime
    weights = cfg.settings.weights

    pairs = _dedupe_pairs(_validation_pairs(cfg, city) + EXTRA_ODS.get(city, []))
    rows: list[dict[str, object]] = []
    for pair in pairs:
        path_v1 = _compute(
            runtime_v1,
            pair,
            radius_m=search.first_mile_radius_m,
            fallback_k=search.first_mile_fallback_k,
            max_seed_nodes=runtime_cfg.max_seed_nodes,
            walk_speed_mps=weights.walk_speed_mps,
            max_time_s=runtime_cfg.max_time_s,
        )
        path_v2 = _compute(
            runtime_v2,
            pair,
            radius_m=search.first_mile_radius_m,
            fallback_k=search.first_mile_fallback_k,
            max_seed_nodes=runtime_cfg.max_seed_nodes,
            walk_speed_mps=weights.walk_speed_mps,
            max_time_s=runtime_cfg.max_time_s,
        )
        s1 = _summary(path_v1)
        s2 = _summary(path_v2)
        rows.append(
            {
                "od": asdict(pair),
                "v1": s1,
                "v2": s2,
                "delta_total_s": s2["total_time_s"] - s1["total_time_s"],
                "changed_reachability": s1["reachable"] != s2["reachable"],
                "changed_transfer_count": s1["transfer_count"] != s2["transfer_count"],
                "changed_rides": s1["ride_labels"] != s2["ride_labels"],
                "changed_signature": s1["segment_signature"] != s2["segment_signature"],
            }
        )

    report = {
        "city": city,
        "pair_count": len(rows),
        "pairs": rows,
    }
    text = json.dumps(report, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
