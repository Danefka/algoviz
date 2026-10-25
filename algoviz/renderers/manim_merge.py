"""Video uses exactly the same recursion-tree frames and timing as Qt."""
from manim import Line, RoundedRectangle, Scene, Text, UpdateFromAlphaFunc, VGroup, linear

from ..playback import DURATIONS, Frame
from .statistics import merge_statistics as statistics
from .merge_layout import CELL_HEIGHT, CELL_WIDTH, VIEW_TOP, visual_merge


class MergeScene(Scene):
    def __init__(self, execution, title, on_progress=None, *,
                 show_title=True, show_indices=True, show_counters=True, show_comments=True, **kwargs):
        self.execution = execution
        self.title = title
        self.on_progress = on_progress or (lambda *_: None)
        self.on_status = lambda message: None
        self.show_title, self.show_indices, self.show_counters = show_title, show_indices, show_counters
        self.show_comments = show_comments
        self.text_cache = {}
        self.cell_objects, self.edge_objects, self.label_objects = {}, {}, {}
        initial = execution["initial_state"]
        picture = visual_merge(Frame(initial, initial, None, 1, 0))
        self.scale = min(12.4 / picture.width, 5.1 / picture.height)
        self.center_y = VIEW_TOP + picture.height / 2
        super().__init__(**kwargs)

    def label(self, value, size=24, color="#24262B", max_width=12.4):
        key = (str(value), size, color, max_width)
        if key not in self.text_cache:
            text = Text(str(value), font_size=size, color=color)
            if text.width > max_width:
                text.scale_to_fit_width(max_width)
            self.text_cache[key] = text
        return self.text_cache[key].copy()

    def point(self, x, y):
        return [x * self.scale, (self.center_y - y) * self.scale + 0.2, 0]

    def sync_picture(self, frame):
        picture = visual_merge(frame)
        # Reuse objects and cached text. No Pango text generation per video frame.
        for box, number, _ in self.cell_objects.values():
            box.set_stroke(opacity=0).set_fill(opacity=0)
            if number is not None:
                number.set_opacity(0)
        for line in self.edge_objects.values():
            line.set_stroke(opacity=0)
        for label in self.label_objects.values():
            label.set_opacity(0)
        for edge in picture.edges:
            start, end = self.point(edge.x1, edge.y1), self.point(edge.x2, edge.y2)
            if start == end:
                end = [end[0], end[1] - 0.0001, 0]
            if edge.key not in self.edge_objects:
                line = Line(start, end, stroke_color="#DFE4EB", stroke_width=1.5)
                self.edge_objects[edge.key] = line
                self.edge_group.add(line)
            line = self.edge_objects[edge.key]
            line.put_start_and_end_on(start, end).set_stroke(opacity=edge.opacity)
        for cell in picture.cells:
            key = (*cell.key, cell.element_id)
            if key not in self.cell_objects:
                box = RoundedRectangle(width=CELL_WIDTH * self.scale, height=CELL_HEIGHT * self.scale,
                                       corner_radius=0.06, stroke_width=1.6)
                number = None if cell.value is None else self.label(
                    cell.value, 25 * self.scale, max_width=CELL_WIDTH * self.scale * 0.82)
                self.cell_objects[key] = (box, number, cell.value)
                self.cell_group.add(box)
                if number is not None:
                    self.cell_group.add(number)
            box, number, _ = self.cell_objects[key]
            point = self.point(cell.x, cell.y)
            box.move_to(point).set_stroke(color=cell.color, opacity=cell.opacity)
            box.set_fill(color=cell.color, opacity=0.10 * cell.opacity)
            if number is not None:
                number.move_to(point).set_opacity(cell.opacity * cell.text_opacity)
        for index, item in enumerate(picture.labels):
            if item.kind == "index" and not self.show_indices:
                continue
            key = (index, item.text, item.kind)
            if key not in self.label_objects:
                label = self.label(item.text, 13 * self.scale if item.kind == "index" else 20,
                                   color="#939BA7")
                self.label_objects[key] = label
                self.label_group.add(label)
            self.label_objects[key].move_to(self.point(item.x, item.y)).set_opacity(item.opacity)

    def construct(self):
        self.camera.background_color = "#FFFFFF"
        self.on_status("Подготовка дерева разбиений…")
        if self.show_title:
            self.add(self.label(self.title, 29, max_width=9).move_to([0, 3.35, 0]))
        self.edge_group, self.cell_group, self.label_group = VGroup(), VGroup(), VGroup()
        tree = VGroup(self.edge_group, self.cell_group, self.label_group)
        before = self.execution["initial_state"]
        self.sync_picture(Frame(before, before, None, 1, 0))
        caption = VGroup()
        if self.show_comments:
            caption.add(self.label("Сначала разделим массив до отдельных элементов", 22).move_to([0, -2.9, 0]))
        counters = VGroup()
        self.add(tree, caption)
        self.wait(0.6)
        steps = self.execution["steps"]
        for number, step in enumerate(steps, start=1):
            self.on_status(f"Рендер дерева: шаг {number} из {len(steps)}…")
            after = step["state_after"]
            self.remove(caption, counters)
            caption = VGroup()
            if self.show_comments:
                caption.add(self.label(step["description"], 22).move_to([0, -2.9, 0]))
            counters = VGroup()
            if self.show_counters:
                counters.add(self.label(statistics(after), 17).move_to([0, -3.5, 0]))
                counters.add(self.label(f"Шаг {number}/{len(steps)}", 16, max_width=2.5)
                             .move_to([5.5, 3.35, 0]))
            self.add(caption, counters)

            # Create all objects before Cairo determines the animation's family.
            for progress in (1, 0.5, 0):
                self.sync_picture(Frame(before, after, step, progress, number))

            def update_tree(mobject, alpha):
                self.sync_picture(Frame(before, after, step, alpha, number))

            self.play(UpdateFromAlphaFunc(tree, update_tree, rate_func=linear),
                      run_time=DURATIONS.get(step["type"], 0.6))
            self.sync_picture(Frame(after, after, step, 1, number))
            before = after
            self.on_progress(number, len(steps))
        self.on_status("Сборка MP4…")
