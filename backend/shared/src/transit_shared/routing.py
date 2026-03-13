from __future__ import annotations

import heapq
from typing import Sequence

from transit_shared.seed_selection import (
    nearest_k_seed_candidates,
    seed_candidates_within_radius,
)

INF = 10**18
__all__ = [
    "INF",
    "seed_candidates_within_radius",
    "nearest_k_seed_candidates",
    "dijkstra_min_times",
    "dijkstra_with_predecessors",
]


def dijkstra_min_times(
    *,
    offsets: Sequence[int],
    targets: Sequence[int],
    weights: Sequence[int],
    seeds: Sequence[tuple[int, int]],
    max_time_s: int,
) -> list[int]:
    n = len(offsets) - 1
    dist = [INF] * n
    heap: list[tuple[int, int]] = []

    for node_idx, cost in seeds:
        if cost < dist[node_idx]:
            dist[node_idx] = cost
            heapq.heappush(heap, (cost, node_idx))

    while heap:
        current, node_idx = heapq.heappop(heap)
        if current != dist[node_idx]:
            continue
        if current > max_time_s:
            continue

        start = offsets[node_idx]
        end = offsets[node_idx + 1]
        for edge_idx in range(start, end):
            nxt = targets[edge_idx]
            cand = current + weights[edge_idx]
            if cand < dist[nxt]:
                dist[nxt] = cand
                heapq.heappush(heap, (cand, nxt))

    return dist


def dijkstra_with_predecessors(
    *,
    offsets: Sequence[int],
    targets: Sequence[int],
    weights: Sequence[int],
    seeds: Sequence[tuple[int, int]],
    max_time_s: int,
) -> tuple[list[int], list[int], list[int]]:
    n = len(offsets) - 1
    dist = [INF] * n
    prev_node = [-1] * n
    prev_edge = [-1] * n
    heap: list[tuple[int, int]] = []

    for node_idx, cost in seeds:
        if cost < dist[node_idx]:
            dist[node_idx] = cost
            heapq.heappush(heap, (cost, node_idx))

    while heap:
        current, node_idx = heapq.heappop(heap)
        if current != dist[node_idx]:
            continue
        if current > max_time_s:
            continue

        start = offsets[node_idx]
        end = offsets[node_idx + 1]
        for edge_idx in range(start, end):
            nxt = targets[edge_idx]
            cand = current + weights[edge_idx]
            if cand > max_time_s:
                continue
            if cand < dist[nxt]:
                dist[nxt] = cand
                prev_node[nxt] = node_idx
                prev_edge[nxt] = edge_idx
                heapq.heappush(heap, (cand, nxt))

    return dist, prev_node, prev_edge
