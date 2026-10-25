"""Seekable playback of semantic steps. No Qt, video files or Manim required."""
from __future__ import annotations

from dataclasses import dataclass
import math


SPEED_PRESETS = (0.5, 1.0, 1.5, 2.0, 4.0)


DURATIONS = {
    "compare": 0.6, "swap": 1.0, "mark_sorted": 0.4, "done": 0.8,
    "focus": 0.6, "pointers": 0.35,
    "split": 1.0, "merge_start": 0.7, "merge_compare": 0.6,
    "merge_copy": 0.85, "merge_commit": 0.7,
}


@dataclass(frozen=True)
class Frame:
    before: dict
    after: dict
    step: dict | None
    progress: float
    number: int


class Timeline:
    """position = completed steps; elapsed = time within the next step.

    Seeking always pauses on an exact snapshot. Pausing during a swap keeps
    its fractional position, so resuming never jumps to a different layout.
    The execution record is treated as read-only by both renderers.
    """

    def __init__(self, execution: dict):
        self.execution = execution
        self.position = 0
        self.elapsed = 0.0
        self.speed = 1.0
        self.running = False
        self.in_transition = False

    @property
    def total(self) -> int:
        return len(self.execution["steps"])

    def state_at(self, position: int) -> dict:
        if position == 0:
            return self.execution["initial_state"]
        return self.execution["steps"][position - 1]["state_after"]

    def seek(self, position: int) -> None:
        self.position = max(0, min(self.total, int(position)))
        self.elapsed = 0.0
        self.running = False
        self.in_transition = False

    def play(self) -> None:
        if self.position == self.total:
            self.seek(0)
        self.running = self.total > 0
        self.in_transition = self.running

    def pause(self) -> None:
        self.running = False

    def forward(self) -> None:
        # During a movement, finish that step; otherwise show the next one.
        self.seek(self.position + 1)

    def backward(self) -> None:
        # First return to the start of an unfinished movement.
        self.seek(self.position if self.in_transition else self.position - 1)

    def set_speed(self, speed: float) -> None:
        if not math.isfinite(speed) or speed <= 0:
            raise ValueError("Скорость должна быть положительным числом.")
        self.speed = speed

    def advance(self, seconds: float) -> None:
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Время должно быть неотрицательным числом.")
        if not self.running:
            return
        self.elapsed += seconds * self.speed
        while self.position < self.total:
            step = self.execution["steps"][self.position]
            duration = DURATIONS.get(step["type"], 0.6)
            if self.elapsed < duration:
                return
            self.elapsed -= duration
            self.position += 1
        self.elapsed = 0.0
        self.running = False
        self.in_transition = False

    def frame(self) -> Frame:
        before = self.state_at(self.position)
        if self.in_transition and self.position < self.total:
            step = self.execution["steps"][self.position]
            duration = DURATIONS.get(step["type"], 0.6)
            return Frame(before, step["state_after"], step,
                         min(1.0, self.elapsed / duration), self.position + 1)
        step = self.execution["steps"][self.position - 1] if self.position else None
        return Frame(before, before, step, 1.0, self.position)
