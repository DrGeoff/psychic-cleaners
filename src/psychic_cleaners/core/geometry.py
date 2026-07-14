"""Strict proper segment intersection, used for beam-crossing detection."""

type Vec = tuple[float, float]


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
