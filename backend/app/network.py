"""A synthetic road graph. Distances/capacities are assumptions, not city GIS."""

from itertools import pairwise

EDGES = [
    {"a": "DEPOT", "b": "Z01", "km": 1.5, "capacity_vpm": 25, "zone": "Z01"},
    {"a": "Z01", "b": "Z04", "km": 2.5, "capacity_vpm": 20, "zone": "Z04"},
    {"a": "DEPOT", "b": "Z03", "km": 1.8, "capacity_vpm": 180, "zone": "Z03"},
    {"a": "Z03", "b": "Z04", "km": 3.2, "capacity_vpm": 150, "zone": "Z04"},
    {"a": "DEPOT", "b": "Z02", "km": 2.4, "capacity_vpm": 220, "zone": "Z02"},
    {"a": "Z02", "b": "Z04", "km": 2.3, "capacity_vpm": 200, "zone": "Z04"},
]


def paths_to(target):
    paths = []

    def visit(path):
        if path[-1] == target:
            paths.append(path)
            return
        for edge in EDGES:
            neighbor = edge["b"] if edge["a"] == path[-1] else edge["a"] if edge["b"] == path[-1] else None
            if neighbor and neighbor not in path:
                visit(path + [neighbor])

    visit(["DEPOT"])
    return sorted(paths, key=lambda p: (len(p), p))


def route_edges(route):
    result = []
    for a, b in pairwise(route):
        edge = next((e for e in EDGES if {e["a"], e["b"]} == {a, b}), None)
        if edge is None:
            raise ValueError(f"Unknown road edge {a} -> {b}")
        result.append(edge)
    return result
