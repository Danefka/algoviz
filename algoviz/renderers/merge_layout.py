"""Stable recursion-tree geometry and continuous transitions for Qt and Manim."""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from ..playback import Frame

CELL_WIDTH, CELL_HEIGHT = 0.70, 0.60
STRIDE, LEAF_PITCH, ROW_GAP = 0.76, 1.04, 1.35
VIEW_TOP = -0.65
COLORS = {"normal": "#C8CED7", "compare": "#C99A48", "copy": "#738AB5",
          "sorted": "#7EAA94", "empty": "#DDE2E9"}


@dataclass(frozen=True)
class MergeCell:
    lane: str
    index: int
    element_id: int | None
    value: int | None
    x: float
    y: float
    role: str
    opacity: float = 1.0
    text_opacity: float = 1.0
    color: str = COLORS["normal"]

    @property
    def key(self):
        return self.lane, self.index


@dataclass(frozen=True)
class Edge:
    key: str
    x1: float
    y1: float
    x2: float
    y2: float
    opacity: float = 1.0


@dataclass(frozen=True)
class Label:
    text: str
    x: float
    y: float
    kind: str = "index"
    opacity: float = 1.0


@dataclass(frozen=True)
class MergePicture:
    cells: list[MergeCell]
    edges: list[Edge]
    labels: list[Label]
    width: float
    height: float


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return a + (b - a) * t


def mix_color(a, b, t):
    return "#" + "".join(f"{round(mix(int(a[i:i + 2], 16), int(b[i:i + 2], 16), t)):02X}"
                          for i in (1, 3, 5))


def node_center(node, count):
    lo, hi = node["range"]
    return ((lo + hi) / 2 - count / 2) * LEAF_PITCH, node["depth"] * ROW_GAP


def cell_position(node, index, count):
    x, y = node_center(node, count)
    lo, hi = node["range"]
    return x + (index - (hi - lo - 1) / 2) * STRIDE, y


def copy_position(start_x, start_y, target_x, target_y, progress):
    t = smooth(progress)
    return mix(start_x, target_x, t), mix(start_y, target_y, t)


def snapshot(state):
    """Geometry depends only on original ranges, never on the active branch."""
    count = len(state["values"])
    values = dict(zip(state["element_ids"], state["values"]))
    active = state["active_node"]
    nodes = state["nodes"]
    cells, edges = {}, {}
    for key, node in nodes.items():
        if node["status"] == "collapsed":
            continue
        lo, hi = node["range"]
        for index in range(hi - lo):
            element_id = node["ids"][index] if index < len(node["ids"]) else None
            role = "empty" if element_id is None else "sorted" if node["status"] == "ready" else "normal"
            opacity = 0.42 if node["status"] == "split" else 1.0
            if node["parent"] == active and nodes[active]["status"] == "merging":
                side = "left" if hi == state["middle"] else "right"
                if index < state["pointers"][side]:
                    opacity = 0.22
            if index in state["selected"].get(key, []):
                role = state["selection_kind"]
            x, y = cell_position(node, index, count)
            cell = MergeCell(key, index, element_id, values.get(element_id), x, y,
                             role, opacity, color=COLORS[role])
            cells[cell.key] = cell
        parent_id = node["parent"]
        if parent_id is not None and nodes[parent_id]["status"] != "collapsed":
            x1, y1 = node_center(nodes[parent_id], count)
            x2, y2 = node_center(node, count)
            edges[key] = Edge(key, x1, y1 + 0.65,
                              x2, y2 - CELL_HEIGHT / 2 - 0.10)
    return cells, edges


def visual_merge(frame: Frame) -> MergePicture:
    after, before = frame.after, frame.before
    count = len(after["values"])
    target, end_edges = snapshot(after)
    moving = before != after and frame.progress < 1
    cells, edges = list(target.values()), list(end_edges.values())
    if moving:
        origin, start_edges = snapshot(before)
        t = smooth(frame.progress)
        cells, edges = [], []
        kind = (frame.step or {}).get("type")
        payload = (frame.step or {}).get("payload", {})
        copy_key = (after["active_node"], payload.get("target_index")) if kind == "merge_copy" else None
        # Keep slots in place while a separate copy travels up the tree.
        for key in dict.fromkeys([*origin, *target]):
            a, b = origin.get(key), target.get(key)
            if a is None:
                node = after["nodes"][key[0]]
                parent = before["nodes"][node["parent"]]
                x, y = cell_position(parent, node["range"][0] - parent["range"][0] + key[1], count)
                a = replace(b, x=x, y=y, opacity=0)
            if b is None:
                b = replace(a, opacity=0)
            cell = replace(b, x=mix(a.x, b.x, t), y=mix(a.y, b.y, t),
                           opacity=mix(a.opacity, b.opacity, t), color=mix_color(a.color, b.color, t))
            if key == copy_key:
                cell = replace(cell, element_id=None, value=None)
            elif a.element_id != b.element_id:
                # Clearing the old parent fades the numbers, not the entire row.
                cell = replace(cell, element_id=a.element_id, value=a.value, text_opacity=1 - t)
            cells.append(cell)
        if copy_key is not None:
            lo, hi = after["range"]
            mid = after["middle"]
            source_id = f"{lo}:{mid}" if payload["from"] == "left" else f"{mid}:{hi}"
            source = origin[(source_id, payload["source_index"])]
            destination = target[copy_key]
            x, y = copy_position(source.x, source.y, destination.x, destination.y, frame.progress)
            cells.append(replace(destination, lane="flight", x=x, y=y,
                                 opacity=min(1.0, frame.progress * 8)))
        for key in dict.fromkeys([*start_edges, *end_edges]):
            a, b = start_edges.get(key), end_edges.get(key)
            appearing = a is None
            if a is None:
                child = after["nodes"][key]
                parent = before["nodes"][child["parent"]]
                lo, hi = child["range"]
                x, y = cell_position(parent, lo - parent["range"][0] + (hi - lo - 1) / 2, count)
                a = replace(b, x2=x, y2=y - CELL_HEIGHT / 2 - 0.10, opacity=0)
            if b is None:
                b = replace(a, opacity=0)
            edge = Edge(key, mix(a.x1, b.x1, t), mix(a.y1, b.y1, t),
                        mix(a.x2, b.x2, t), mix(a.y2, b.y2, t), mix(a.opacity, b.opacity, t))
            if appearing:
                # Reveal links only after the rows have separated; never draw through numbers.
                edge = replace(edge, opacity=edge.opacity * min(1, max(0, (edge.y2 - edge.y1) / 0.30)))
            edges.append(edge)
    labels = [Label(str(cell.index), cell.x, cell.y + 0.43, opacity=cell.opacity)
              for cell in cells if cell.lane != "flight"]
    if moving and (frame.step or {}).get("type") == "split":
        labels = [replace(label, opacity=label.opacity * max(0, (smooth(frame.progress) - 0.55) / 0.45))
                  if cell.lane not in before["nodes"] else label
                  for cell, label in zip(cells, labels)]
    if count == 0:
        labels = [Label("Пустой массив", 0, 0, "message")]
    depth = math.ceil(math.log2(max(1, count)))
    # Fix the viewport from the original input: no zoom or reflow between steps.
    return MergePicture(cells, edges, labels, max(7.5, count * LEAF_PITCH + 0.8),
                        max(3.5, depth * ROW_GAP + 1.35))
