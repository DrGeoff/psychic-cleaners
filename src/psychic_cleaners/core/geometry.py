"""Strict proper segment intersection, and straight-line approach-and-stop
motion shared by wisps (core/city.py) and the convergence walkers
(core/convergence.py)."""

import math

type Vec = tuple[float, float]


def move_toward(
    x: float, y: float, target_x: float, target_y: float, max_step: float, stop_radius: float = 0.0
) -> tuple[float, float]:
    """Step (x, y) toward (target_x, target_y) by at most max_step, never
    closer than stop_radius. Already within stop_radius: unchanged."""
    dx = target_x - x
    dy = target_y - y
    length = math.hypot(dx, dy)
    if length <= stop_radius:
        return x, y
    step = min(max_step, length - stop_radius)
    return x + dx / length * step, y + dy / length * step


def _orient(a: Vec, b: Vec, c: Vec) -> float:
    """Twice the signed area of triangle abc (positive = counter-clockwise)."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segments_cross(a1: Vec, a2: Vec, b1: Vec, b2: Vec) -> bool:
    """True iff the open segments a1-a2 and b1-b2 properly intersect.

    Strict test via orientation cross products: the endpoints of each segment
    must lie strictly on opposite sides of the other segment's line. Parallel
    or collinear segments, T-touches, and shared endpoints all return False,
    because at least one orientation is exactly zero (or has equal signs).
    """
    d1 = _orient(b1, b2, a1)
    d2 = _orient(b1, b2, a2)
    d3 = _orient(a1, a2, b1)
    d4 = _orient(a1, a2, b2)
    return d1 * d2 < 0 and d3 * d4 < 0
