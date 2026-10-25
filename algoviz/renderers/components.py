"""Reusable drawing components. No Qt, Manim or task-specific rules."""
from dataclasses import dataclass, field, replace
from typing import Any

COLORS = {"normal": "#C8CED7", "active": "#738AB5", "compare": "#C99A48",
          "matched": "#7EAA94", "error": "#C36A70"}


@dataclass(frozen=True)
class Cell:
    object_id: str
    element_id: Any
    index: int
    value: Any
    x: float
    y: float
    width: float
    height: float
    color: str = COLORS["normal"]
    opacity: float = 1.0

    @property
    def key(self):
        return self.object_id, self.element_id


@dataclass(frozen=True)
class Label:
    key: str
    text: str
    x: float
    y: float
    kind: str = "label"
    opacity: float = 1.0


@dataclass(frozen=True)
class Line:
    key: str
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class Block:
    cells: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    lines: list = field(default_factory=list)


@dataclass
class Picture(Block):
    width: float = 12
    height: float = 6
    top: float = -1.2


def array_view(snapshot, object_id, *, x=0, y=0, title="Массив", roles=None):
    roles = roles or {}
    block = Block()
    count = len(snapshot["values"])
    for index, (element_id, value) in enumerate(zip(snapshot["element_ids"], snapshot["values"])):
        center = x + (index - (count - 1) / 2) * 0.78
        block.cells.append(Cell(object_id, element_id, index, value, center, y, 0.68, 0.60,
                                COLORS[roles.get(element_id, "normal")]))
        block.labels.append(Label(f"{object_id}:index:{index}", str(index), center, y + 0.48, "index"))
    block.labels.append(Label(f"{object_id}:title", title, x, y - 0.85))
    if not count:
        block.labels.append(Label(f"{object_id}:empty", "Пустой массив", x, y))
    return block


def compose(*blocks, width=12, height=6, top=-1.2):
    picture = Picture(width=width, height=height, top=top)
    for block in blocks:
        picture.cells.extend(block.cells)
        picture.labels.extend(block.labels)
        picture.lines.extend(block.lines)
    if len({cell.key for cell in picture.cells}) != len(picture.cells):
        raise ValueError("У компонентов должны быть разные object_id.")
    return picture


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return "#" + "".join(f"{round(mix(int(a[i:i+2], 16), int(b[i:i+2], 16), t)):02X}" for i in (1, 3, 5))


def interpolate(before, after, progress, *, entering=None, leaving=None):
    """Interpolate a composed scene; transfers are explicit object/item coordinates."""
    if progress <= 0:
        return before
    if progress >= 1:
        return after
    entering, leaving = entering or {}, leaving or {}
    t = smooth(progress)
    picture = Picture(lines=after.lines, width=after.width, height=after.height, top=after.top)
    old, new = ({cell.key: cell for cell in p.cells} for p in (before, after))
    for key in dict.fromkeys([*old, *new]):
        a, b = old.get(key), new.get(key)
        if a is None:
            x, y = entering.get(key, (b.x, b.y))
            a = replace(b, x=x, y=y, opacity=0)
        if b is None:
            x, y = leaving.get(key, (a.x, a.y))
            b = replace(a, x=x, y=y, opacity=0)
        picture.cells.append(replace(b, x=mix(a.x, b.x, t), y=mix(a.y, b.y, t),
                                     width=mix(a.width, b.width, t), height=mix(a.height, b.height, t),
                                     color=mix_color(a.color, b.color, t), opacity=mix(a.opacity, b.opacity, t)))
    old, new = ({label.key: label for label in p.labels} for p in (before, after))
    for key in dict.fromkeys([*old, *new]):
        a, b = old.get(key), new.get(key)
        a = a or replace(b, opacity=0)
        b = b or replace(a, opacity=0)
        picture.labels.append(replace(b, x=mix(a.x, b.x, t), y=mix(a.y, b.y, t),
                                      opacity=mix(a.opacity, b.opacity, t)))
    return picture
