"""The shared array scene supports swaps, ranges, pivot IDs and named pointers."""
from manim import FadeIn, Line, RoundedRectangle, Scene, Text, UpdateFromAlphaFunc, VGroup, linear

from ..playback import DURATIONS, Frame
from .array_layout import COLORS, array_geometry, visual_cells, visual_guides
from .statistics import array_statistics

TEXT = "#24262B"
MUTED = "#777D87"


class ArrayScene(Scene):
    def __init__(self, execution, title, on_progress=None, *,
                 show_title=True, show_indices=True, show_counters=True, show_comments=True, **kwargs):
        self.title, self.execution = title, execution
        self.show_title, self.show_indices = show_title, show_indices
        self.show_counters, self.show_comments = show_counters, show_comments
        self.on_progress = on_progress or (lambda *_: None)
        self.on_status = lambda message: None
        self.text_cache = {}
        self.cells = {}
        self.geometry = array_geometry(854, 320, len(execution["initial_state"]["values"]))
        self.scale = 12.4 / 854
        super().__init__(**kwargs)

    def label(self, text, size=24, color=TEXT, max_width=12.4):
        key = str(text), size, color, max_width
        if key not in self.text_cache:
            result = Text(str(text), font_size=size, color=color)
            if result.width > max_width:
                result.scale_to_fit_width(max_width)
            self.text_cache[key] = result
        return self.text_cache[key].copy()

    def point(self, x, y):
        return [(x - 427) * self.scale, (160 - y) * self.scale + 0.25, 0]

    def sync_cells(self, frame):
        geometry = self.geometry
        for cell in visual_cells(frame):
            box, number = self.cells[cell.element_id]
            point = self.point(geometry.start_x + cell.slot * geometry.stride + geometry.cell_width / 2,
                               geometry.center_y + cell.lift * geometry.lift_height)
            border = COLORS["pivot"] if cell.pivot else COLORS[cell.role]
            box.move_to(point).set_stroke(color=border, width=3 if cell.pivot else 1.8, opacity=cell.opacity)
            box.set_fill(color=COLORS[cell.role], opacity=0.10 * cell.opacity)
            number.move_to(point).set_color(COLORS["pivot"] if cell.pivot else TEXT).set_opacity(cell.opacity)

    def make_guides(self, frame):
        guides, geometry = visual_guides(frame), self.geometry
        result = VGroup()
        if guides.active_range is not None:
            lo, hi = guides.active_range
            left = geometry.start_x + lo * geometry.stride
            right = geometry.start_x + (hi - 1) * geometry.stride + geometry.cell_width
            y = geometry.range_y
            for a, b in (((left, y + 5), (left, y)), ((left, y), (right, y)),
                         ((right, y), (right, y + 5))):
                result.add(Line(self.point(*a), self.point(*b), stroke_color=COLORS["pivot"], stroke_width=1.5))
            if guides.pivot_value is not None:
                result.add(self.label(f"Опора: {guides.pivot_value}", 17, COLORS["pivot"])
                           .move_to(self.point(427, y - 13)))
        for index, names in guides.pointers:
            x = geometry.start_x + index * geometry.stride + geometry.cell_width / 2
            result.add(self.label(names, 15, COLORS["pivot"], max_width=(geometry.cell_width + 6) * self.scale)
                       .move_to(self.point(x, geometry.pointer_y + 8)))
        return result

    def construct(self):
        self.on_status("Подготовка сцены…")
        self.camera.background_color = "#FFFFFF"
        geometry = self.geometry
        before = self.execution["initial_state"]
        if self.show_title:
            self.add(self.label(self.title, 30).move_to([0, 3.35, 0]))

        group = VGroup()
        for index, (element_id, value) in enumerate(zip(before["element_ids"], before["values"])):
            self.on_status(f"Создание элемента {index + 1} из {len(before['values'])}…")
            box = RoundedRectangle(width=geometry.cell_width * self.scale,
                                   height=geometry.cell_height * self.scale,
                                   corner_radius=0.10, stroke_width=1.8)
            number = self.label(value, 28, max_width=geometry.cell_width * self.scale * 0.78)
            self.cells[element_id] = box, number
            group.add(box, number)
            if self.show_indices:
                x = geometry.start_x + index * geometry.stride + geometry.cell_width / 2
                self.add(self.label(index, 16, MUTED).move_to(self.point(x, geometry.index_y + 8)))
        initial_frame = Frame(before, before, None, 1, 0)
        self.sync_cells(initial_frame)
        guides = self.make_guides(initial_frame)
        caption, counters = VGroup(), VGroup()
        if self.show_comments:
            caption.add(self.label("Начальный массив", 23).move_to([0, -2.75, 0]))
        if self.show_counters:
            counters.add(self.label(array_statistics(before), 18, MUTED).move_to([0, -3.35, 0]))
            counters.add(self.label("Начало", 16, MUTED).move_to([0, 2.85, 0]))
        self.add(guides, caption, counters)
        self.on_status("Рендер первых кадров…")
        if self.cells:
            self.play(FadeIn(group), run_time=0.35)
        else:
            self.add(self.label("Пустой массив", 26).move_to(self.point(427, geometry.center_y)))
        self.wait(0.35)

        steps = self.execution["steps"]
        for number, step in enumerate(steps, 1):
            self.on_status(f"Рендер шага {number} из {len(steps)}…")
            after = step["state_after"]
            self.remove(guides, caption, counters)
            guides = self.make_guides(Frame(before, after, step, 0, number))
            caption, counters = VGroup(), VGroup()
            if self.show_comments:
                caption.add(self.label(step["description"], 23).move_to([0, -2.75, 0]))
            if self.show_counters:
                counters.add(self.label(array_statistics(after), 18, MUTED).move_to([0, -3.35, 0]))
                counters.add(self.label(f"Шаг {number}/{len(steps)}", 16, MUTED).move_to([0, 2.85, 0]))
            self.add(guides, caption, counters)
            duration = DURATIONS.get(step["type"], 0.6)
            if step["type"] == "swap":
                self.sync_cells(Frame(before, after, step, 0, number))

                def update_cells(mobject, alpha):
                    self.sync_cells(Frame(before, after, step, alpha, number))

                self.play(UpdateFromAlphaFunc(group, update_cells, rate_func=linear), run_time=duration)
            else:
                self.sync_cells(Frame(before, after, step, 1, number))
                self.wait(duration)
            self.sync_cells(Frame(after, after, step, 1, number))
            before = after
            self.on_progress(number, len(steps))
        self.on_status("Сборка MP4…")
