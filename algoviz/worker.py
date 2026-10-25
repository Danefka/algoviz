from __future__ import annotations

import faulthandler
import json
from pathlib import Path
import shutil
import traceback

from .core import validate_execution
from .registry import get_algorithm
from .renderers.registry import get_visualization

EVENT_PREFIX = "ALGOVIZ_EVENT:"
QUALITY_PRESETS = {
    "preview": (854, 480, 15),
    "hd": (1280, 720, 30),
}


def emit(kind, **data):
    print(EVENT_PREFIX + json.dumps({"kind": kind, **data}, ensure_ascii=False), flush=True)


def render_job(job_file: str) -> int:
    def report(kind, **data):
        # If one stage stops reporting progress, expose its Python stack in
        # the export log. This diagnoses a delay; it does not stop the render.
        if kind in {"status", "progress"}:
            faulthandler.cancel_dump_traceback_later()
            faulthandler.dump_traceback_later(45, repeat=True)
        emit(kind, **data)

    try:
        job_path = Path(job_file).resolve()
        job = json.loads(job_path.read_text(encoding="utf-8"))
        execution = job["execution"]
        validate_execution(execution)
        width, height, fps = QUALITY_PRESETS[job["quality"]]
        report("status", message="Загрузка библиотеки Manim…")
        from manim import tempconfig
        report("status", message="Manim загружен. Подготовка сцены…")
        algorithm = get_algorithm(execution["algorithm"])
        visualization = get_visualization(algorithm.visualization)

        with tempconfig({
            "renderer": "cairo",
            "media_dir": str(job_path.parent / "media"),
            "output_file": algorithm.id,
            "pixel_width": width,
            "pixel_height": height,
            "frame_rate": fps,
            "frame_height": 8.0,
            "frame_width": 14.2222222222,
            "format": "mp4",
            "write_to_movie": True,
            "save_last_frame": False,
            "preview": False,
            "disable_caching": True,
            "progress_bar": "none",
            "verbosity": "WARNING",
        }):
            scene = visualization.create_scene(
                execution, algorithm,
                on_progress=lambda current, total: report("progress", current=current, total=total),
                options=job.get("options", {}),
            )
            scene.on_status = lambda message: report("status", message=message)
            report("status", message="Запуск рендера…")
            scene.render()
            rendered = Path(scene.renderer.file_writer.movie_file_path)
        if not rendered.is_file() or rendered.stat().st_size == 0:
            raise RuntimeError("Manim завершился, но видео не создано.")
        report("status", message="Сохранение готового видео…")
        destination = job_path.parent / "result.mp4"
        shutil.copy2(rendered, destination)
        emit("complete", path=str(destination))
        return 0
    except Exception as exc:
        traceback.print_exc()
        if isinstance(exc, ModuleNotFoundError):
            message = ("Не найдены зависимости Manim. Запустите приложение командой "
                       "uv run --extra export python main.py и проверьте README.md.")
        else:
            message = f"Не удалось создать видео: {exc}"
        emit("error", message=message)
        return 1
    finally:
        faulthandler.cancel_dump_traceback_later()
