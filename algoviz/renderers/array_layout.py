"""Array-specific positions; the timeline itself does not know about cells."""
from __future__ import annotations

from dataclasses import dataclass
from ..playback import Frame

COLORS = {"normal": "#D5D8DE", "compare": "#BF8B30", "swap": "#7363AE",
          "sorted": "#43856B", "pivot": "#42789D"}


@dataclass(frozen=True)
class Cell:
    element_id: int
    value: int
    slot: float
    lift: float
    role: str
    opacity: float = 1.0
    pivot: bool = False


@dataclass(frozen=True)
class Guides:
    active_range: tuple | None
    pivot_value: int | None
    pointers: tuple


def visual_guides(frame: Frame) -> Guides:
    """Index pointers stay at positions; equal positions share a short label."""
    state = frame.after
    focus = state.get("focus", {})
    active_range = focus.get("range")
    pivot_id = focus.get("pivot_id")
    pivot_value = None
    if pivot_id is not None:
        pivot_value = state["values"][state["element_ids"].index(pivot_id)]
    groups = {}
    for name, index in sorted(focus.get("pointers", {}).items()):
        groups.setdefault(index, []).append(name)
    return Guides(None if active_range is None else tuple(active_range), pivot_value,
                  tuple((index, " · ".join(names)) for index, names in sorted(groups.items())))


@dataclass(frozen=True)
class Geometry:
    start_x: float
    center_y: float
    cell_width: float
    cell_height: float
    stride: float
    lift_height: float
    index_y: float
    pointer_y: float
    range_y: float


def array_geometry(width, height, count):
    """Reserve guide lanes and clearance over stationary cells at any window size."""
    gap = 10.0 if count <= 8 else 6.0
    cell_width = min(78.0, (width - 36.0 - gap * max(0, count - 1)) / max(1, count))
    cell_height = min(72.0, max(50.0, cell_width), (height - 92.0) / 3.0)
    lift_height = cell_height + 8.0
    span = count * cell_width + max(0, count - 1) * gap
    center_y = (height - 12.0) / 2.0
    index_y = center_y + cell_height / 2 + lift_height + 8
    return Geometry((width - span) / 2, center_y, cell_width, cell_height, cell_width + gap,
                    lift_height, index_y, index_y + 20,
                    center_y - cell_height / 2 - lift_height - 10)


def swap_position(start: float, target: float, progress: float) -> tuple[float, float]:
    """Separate, cross and return with overlapping, rounded transitions.

    Both renderers share this path. Positive lift means down on screen;
    the element moving right goes up. Quintic easing keeps velocity and
    acceleration continuous; overlapping axes avoid stops at the corners.
    """
    if start == target:
        return float(start), 0.0
    progress = max(0.0, min(1.0, progress))

    def smooth(value):
        value = max(0.0, min(1.0, value))
        return max(0.0, min(1.0, value ** 3 * (value * (value * 6.0 - 15.0) + 10.0)))

    if abs(target - start) > 1:
        # Clear stationary cells before crossing them. The phases still overlap.
        horizontal = smooth((progress - 0.25) / 0.50)
        lift = smooth(progress / 0.30) * smooth((1.0 - progress) / 0.30)
    else:
        horizontal = smooth((progress - 0.15) / 0.70)
        lift = smooth(progress / 0.40) * smooth((1.0 - progress) / 0.40)
    direction = -1 if start < target else 1
    return start + (target - start) * horizontal, direction * lift


def visual_cells(frame: Frame) -> list[Cell]:
    """Interpolate stable element IDs, including when values are duplicates.

    slot is an array index (possibly fractional); lift is in [-1, 1].
    The Qt canvas converts those logical coordinates to screen pixels.
    """
    before = frame.before
    after = frame.after
    destination = {element_id: index for index, element_id in enumerate(after["element_ids"])}
    step = frame.step or {}
    active = set(step.get("payload", {}).get("indices", []))
    sorted_positions = set(after["sorted_indices"])
    focus = after.get("focus", {})
    active_range = focus.get("range")
    kind = step.get("type")
    cells = []
    for index, (element_id, value) in enumerate(zip(before["element_ids"], before["values"])):
        target = destination[element_id]
        role = "sorted" if target in sorted_positions else "normal"
        if kind in {"compare", "swap"} and target in active:
            role = kind
        slot, lift = swap_position(index, target, frame.progress)
        outside = active_range is not None and not active_range[0] <= target < active_range[1]
        opacity = (0.62 if target in sorted_positions else 0.26) if outside else 1.0
        pivot = element_id == focus.get("pivot_id") and target not in sorted_positions
        cells.append(Cell(element_id, value, slot, lift, role, opacity, pivot))
    return cells
