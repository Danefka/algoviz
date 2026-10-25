"""Generic Manim renderer for composed structure views."""
from manim import Line, RoundedRectangle, Scene, Text, UpdateFromAlphaFunc, VGroup, linear
from ..playback import DURATIONS, Frame


class CompositeScene(Scene):
    def __init__(self, execution, title, layout, statistics, on_progress=None, *,
                 show_title=True, show_indices=True, show_counters=True, show_comments=True, **kwargs):
        self.execution, self.title = execution, title
        self.layout_fn, self.statistics = layout, statistics
        self.on_progress = on_progress or (lambda *_: None)
        self.on_status = lambda message: None
        self.show_title, self.show_indices, self.show_counters = show_title, show_indices, show_counters
        self.show_comments = show_comments
        initial = execution["initial_state"]
        picture = layout(Frame(initial, initial, None, 1, 0))
        self.scale = min(12.4 / picture.width, 5.1 / picture.height)
        self.center_y = picture.top + picture.height / 2
        self.text_cache, self.cell_objects, self.line_objects, self.label_objects = {}, {}, {}, {}
        super().__init__(**kwargs)

    def label(self, value, size=24, color="#24262B", max_width=12.4):
        key = str(value), size, color, max_width
        if key not in self.text_cache:
            text = Text(str(value), font_size=size, color=color)
            if text.width > max_width:
                text.scale_to_fit_width(max_width)
            self.text_cache[key] = text
        return self.text_cache[key].copy()

    def point(self, x, y):
        return [x * self.scale, (self.center_y - y) * self.scale + 0.2, 0]

    def sync_picture(self, frame):
        picture = self.layout_fn(frame)
        for box, text in self.cell_objects.values():
            box.set_stroke(opacity=0).set_fill(opacity=0)
            text.set_opacity(0)
        for line in self.line_objects.values():
            line.set_stroke(opacity=0)
        for text in self.label_objects.values():
            text.set_opacity(0)
        for line in picture.lines:
            start, end = self.point(line.x1, line.y1), self.point(line.x2, line.y2)
            if line.key not in self.line_objects:
                item = Line(start, end, stroke_color="#DDE2E9", stroke_width=1.5)
                self.line_objects[line.key] = item
                self.lines.add(item)
            self.line_objects[line.key].put_start_and_end_on(start, end).set_stroke(opacity=1)
        for cell in picture.cells:
            key = (*cell.key, str(cell.value))
            if key not in self.cell_objects:
                box = RoundedRectangle(width=cell.width * self.scale, height=cell.height * self.scale,
                                       corner_radius=0.05, stroke_width=1.6)
                text = self.label(cell.value, 27 * self.scale, max_width=cell.width * self.scale * 0.8)
                self.cell_objects[key] = box, text
                self.cells.add(box, text)
            box, text = self.cell_objects[key]
            point = self.point(cell.x, cell.y)
            box.stretch_to_fit_width(cell.width * self.scale).stretch_to_fit_height(cell.height * self.scale)
            box.move_to(point).set_stroke(color=cell.color, opacity=cell.opacity)
            box.set_fill(color=cell.color, opacity=0.10 * cell.opacity)
            text.move_to(point).set_opacity(cell.opacity)
        for label in picture.labels:
            if label.kind == "index" and not self.show_indices:
                continue
            key = label.key, label.text
            if key not in self.label_objects:
                text = self.label(label.text, 13 * self.scale if label.kind == "index" else 18,
                                  color="#878C96", max_width=3.3)
                self.label_objects[key] = text
                self.labels.add(text)
            self.label_objects[key].move_to(self.point(label.x, label.y)).set_opacity(label.opacity)

    def construct(self):
        self.camera.background_color = "#FFFFFF"
        self.on_status("Подготовка составной визуализации…")
        if self.show_title:
            self.add(self.label(self.title, 29, max_width=9).move_to([0, 3.35, 0]))
        self.lines, self.cells, self.labels = VGroup(), VGroup(), VGroup()
        picture = VGroup(self.lines, self.cells, self.labels)
        before = self.execution["initial_state"]
        self.sync_picture(Frame(before, before, None, 1, 0))
        caption = VGroup()
        if self.show_comments:
            caption.add(self.label("Начальное состояние", 22).move_to([0, -2.9, 0]))
        counters = VGroup()
        self.add(picture, caption)
        self.wait(0.6)
        steps = self.execution["steps"]
        for number, step in enumerate(steps, 1):
            after = step["state_after"]
            self.on_status(f"Рендер шага {number} из {len(steps)}…")
            self.remove(caption, counters)
            caption = VGroup()
            if self.show_comments:
                caption.add(self.label(step["description"], 22).move_to([0, -2.9, 0]))
            counters = VGroup()
            if self.show_counters:
                counters.add(self.label(self.statistics(after), 17).move_to([0, -3.5, 0]))
                counters.add(self.label(f"Шаг {number}/{len(steps)}", 16, max_width=2.5).move_to([5.5, 3.35, 0]))
            self.add(caption, counters)
            for progress in (1, 0.5, 0):
                self.sync_picture(Frame(before, after, step, progress, number))

            def update_picture(mobject, alpha):
                self.sync_picture(Frame(before, after, step, alpha, number))

            self.play(UpdateFromAlphaFunc(picture, update_picture, rate_func=linear),
                      run_time=DURATIONS.get(step["type"], 0.6))
            self.sync_picture(Frame(after, after, step, 1, number))
            before = after
            self.on_progress(number, len(steps))
        self.on_status("Сборка MP4…")
