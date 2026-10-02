"""Structural cross-checks, not a replacement for the general producer."""
from __future__ import annotations
from .model import validate


def vanishing_value(xs: set[int], z: int, q: int) -> int:
    y = 1
    for x in sorted(xs):
        y = y * (1 - z * pow(x, -1, q)) % q
    return y


def saturated_verdict(trace: dict) -> str:
    validate(trace)
    q, k = trace["field"], trace["threshold"]
    if trace["epochs"] != 2:
        raise ValueError("two epochs required")
    sets = [{ob["x"] for ob in trace["observations"] if ob["kind"] == "snapshot" and ob["epoch"] == e} for e in range(2)]
    if any(len(s) != k - 1 for s in sets):
        raise ValueError("each snapshot set must contain threshold minus one coordinates")
    same = all(vanishing_value(sets[0], ob["x"], q) == vanishing_value(sets[1], ob["x"], q)
               for ob in trace["observations"] if ob["kind"] == "delta")
    return "hiding" if same else "revealing"


def snapshot_verdict(trace: dict) -> str:
    validate(trace)
    if any(ob["kind"] != "snapshot" for ob in trace["observations"]):
        raise ValueError("snapshot-only trace required")
    sizes = [len({ob['x'] for ob in trace['observations'] if ob['epoch'] == e}) for e in range(trace['epochs'])]
    return "revealing" if max(sizes, default=0) >= trace["threshold"] else "hiding"


def anchored_closure(trace: dict) -> tuple[bool, list[list[int]]]:
    """Return whether every nontrivial coordinate component is anchored, and closure."""
    validate(trace)
    t = trace["epochs"]
    closure = [set() for _ in range(t)]
    coords = {ob["x"] for ob in trace["observations"]}
    all_anchored = True
    for x in sorted(coords):
        adjacency = {e: set() for e in range(t)}
        anchors = set()
        for ob in trace["observations"]:
            if ob["x"] != x:
                continue
            if ob["kind"] == "snapshot":
                anchors.add(ob["epoch"])
            else:
                u, v = ob["before"], ob["after"]
                adjacency[u].add(v); adjacency[v].add(u)
        visited = set()
        for root in range(t):
            if root in visited:
                continue
            component = set(); todo = [root]
            while todo:
                e = todo.pop()
                if e in component:
                    continue
                component.add(e); todo.extend(adjacency[e] - component)
            visited |= component
            if component & anchors:
                for e in component:
                    closure[e].add(x)
            elif any(adjacency[e] for e in component):
                all_anchored = False
    return all_anchored, [sorted(s) for s in closure]
