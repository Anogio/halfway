from __future__ import annotations

from collections import defaultdict

from transit_backend.core.isochrone_topology import GridTopology


def dissolve_cells_to_multipolygon(
    cells: set[tuple[int, int]],
    topology: GridTopology,
) -> list[list[list[list[float]]]]:
    if not cells:
        return []

    multipolygon: list[list[list[list[float]]]] = []
    lon_cache: dict[int, float] = {}
    lat_cache: dict[int, float] = {}
    for component in _connected_components(cells):
        edges = _boundary_edges(component)
        loops = _extract_loops(edges)

        outer_loops: list[list[tuple[int, int]]] = []
        hole_loops: list[list[tuple[int, int]]] = []

        for loop in loops:
            simplified_loop = _simplify_axis_aligned_loop(loop)
            area = _signed_area(simplified_loop)
            if area > 0:
                outer_loops.append(simplified_loop)
            elif area < 0:
                hole_loops.append(simplified_loop)

        polygons: list[list[list[tuple[int, int]]]] = [[outer] for outer in outer_loops]
        outer_metadata = [
            {
                "outer": outer,
                "area": abs(_signed_area(outer)),
                "bounds": _ring_bounds(outer),
            }
            for outer in outer_loops
        ]
        if not polygons:
            continue

        for hole in hole_loops:
            point = hole[0]
            container_idx = _container_polygon_index(polygons, point, outer_metadata=outer_metadata)
            if container_idx is None:
                continue
            polygons[container_idx].append(hole)

        for polygon_rings in polygons:
            rings_coords = [
                _ring_to_lon_lat(ring, topology, lon_cache=lon_cache, lat_cache=lat_cache)
                for ring in polygon_rings
            ]
            if rings_coords:
                multipolygon.append(rings_coords)
    return multipolygon


def _connected_components(cells: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    components: list[set[tuple[int, int]]] = []
    remaining = set(cells)

    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = {seed}
        while stack:
            row, col = stack.pop()
            for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                component.add(neighbor)
                stack.append(neighbor)
        components.append(component)

    return components


def _boundary_edges(cells: set[tuple[int, int]]) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for row, col in cells:
        south_neighbor = (row - 1, col)
        east_neighbor = (row, col + 1)
        north_neighbor = (row + 1, col)
        west_neighbor = (row, col - 1)

        # x = column, y = row on integer lattice.
        if south_neighbor not in cells:
            edges.add(((col, row), (col + 1, row)))
        if east_neighbor not in cells:
            edges.add(((col + 1, row), (col + 1, row + 1)))
        if north_neighbor not in cells:
            edges.add(((col + 1, row + 1), (col, row + 1)))
        if west_neighbor not in cells:
            edges.add(((col, row + 1), (col, row)))
    return edges


def _extract_loops(
    edges: set[tuple[tuple[int, int], tuple[int, int]]],
) -> list[list[tuple[int, int]]]:
    adjacency: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for start, end in edges:
        adjacency[start].add(end)

    remaining = set(edges)
    loops: list[list[tuple[int, int]]] = []
    while remaining:
        start, nxt = remaining.pop()
        loop = [start, nxt]
        _remove_edge(adjacency, start, nxt)

        prev = start
        current = nxt
        while current != start:
            candidates = adjacency.get(current)
            if not candidates:
                raise ValueError("invalid boundary graph: dangling edge")

            next_vertex = _select_next_vertex(prev, current, candidates)
            edge = (current, next_vertex)
            if edge not in remaining:
                raise ValueError("invalid boundary graph: broken loop")
            remaining.remove(edge)
            _remove_edge(adjacency, current, next_vertex)
            loop.append(next_vertex)
            prev, current = current, next_vertex
        loops.append(loop)

    return loops


def _remove_edge(
    adjacency: dict[tuple[int, int], set[tuple[int, int]]],
    start: tuple[int, int],
    end: tuple[int, int],
) -> None:
    outgoing = adjacency.get(start)
    if not outgoing:
        return
    outgoing.discard(end)
    if not outgoing:
        adjacency.pop(start, None)


def _select_next_vertex(
    prev: tuple[int, int],
    current: tuple[int, int],
    candidates: set[tuple[int, int]],
) -> tuple[int, int]:
    dx = current[0] - prev[0]
    dy = current[1] - prev[1]
    if abs(dx) + abs(dy) != 1:
        raise ValueError("invalid edge direction")

    left = (-dy, dx)
    straight = (dx, dy)
    right = (dy, -dx)
    back = (-dx, -dy)

    for ndx, ndy in (left, straight, right, back):
        candidate = (current[0] + ndx, current[1] + ndy)
        if candidate in candidates:
            return candidate

    raise ValueError("invalid boundary graph: no continuation found")


def _signed_area(loop: list[tuple[int, int]]) -> float:
    area = 0.0
    for i in range(len(loop) - 1):
        x1, y1 = loop[i]
        x2, y2 = loop[i + 1]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def _simplify_axis_aligned_loop(loop: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(loop) <= 4:
        return loop
    points = loop[:-1]
    if len(points) <= 3:
        return loop

    simplified: list[tuple[int, int]] = []
    point_count = len(points)
    for idx, current in enumerate(points):
        prev = points[idx - 1]
        nxt = points[(idx + 1) % point_count]
        if (prev[0] == current[0] == nxt[0]) or (prev[1] == current[1] == nxt[1]):
            continue
        simplified.append(current)

    if not simplified:
        return loop
    simplified.append(simplified[0])
    return simplified


def _container_polygon_index(
    polygons: list[list[list[tuple[int, int]]]],
    point: tuple[int, int],
    *,
    outer_metadata: list[dict[str, object]] | None = None,
) -> int | None:
    candidate_idx: int | None = None
    candidate_area = float("inf")
    for idx, polygon in enumerate(polygons):
        outer = polygon[0]
        info = outer_metadata[idx] if outer_metadata is not None and idx < len(outer_metadata) else None
        bounds = info["bounds"] if isinstance(info, dict) else _ring_bounds(outer)
        if not _point_in_bounds(point, bounds):
            continue
        if not _point_in_ring(point, outer):
            continue
        area = float(info["area"]) if isinstance(info, dict) else abs(_signed_area(outer))
        if area < candidate_area:
            candidate_idx = idx
            candidate_area = area
    return candidate_idx


def _ring_bounds(ring: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    xs = [x for x, _ in ring]
    ys = [y for _, y in ring]
    return min(xs), min(ys), max(xs), max(ys)


def _point_in_bounds(point: tuple[int, int], bounds: tuple[int, int, int, int]) -> bool:
    x, y = point
    min_x, min_y, max_x, max_y = bounds
    return min_x <= x <= max_x and min_y <= y <= max_y


def _point_in_ring(point: tuple[int, int], ring: list[tuple[int, int]]) -> bool:
    x, y = point
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
        )
        if intersects:
            inside = not inside
    return inside


def _ring_to_lon_lat(
    ring: list[tuple[int, int]],
    topology: GridTopology,
    *,
    lon_cache: dict[int, float] | None = None,
    lat_cache: dict[int, float] | None = None,
) -> list[list[float]]:
    result: list[list[float]] = []
    for x, y in ring:
        if lon_cache is not None:
            lon = lon_cache.get(x)
            if lon is None:
                lon = round(topology.min_lon + (x - 0.5) * topology.lon_step, 7)
                lon_cache[x] = lon
        else:
            lon = round(topology.min_lon + (x - 0.5) * topology.lon_step, 7)
        if lat_cache is not None:
            lat = lat_cache.get(y)
            if lat is None:
                lat = round(topology.min_lat + (y - 0.5) * topology.lat_step, 7)
                lat_cache[y] = lat
        else:
            lat = round(topology.min_lat + (y - 0.5) * topology.lat_step, 7)
        result.append([lon, lat])
    return result
