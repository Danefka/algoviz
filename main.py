from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--render":
        from algoviz.worker import render_job
        return render_job(sys.argv[2])
    if sys.version_info < (3, 10):
        print("Нужен Python 3.10–3.13. Рекомендуемый запуск: uv run python main.py", file=sys.stderr)
        return 1
    try:
        from PySide6.QtWidgets import QApplication
        from algoviz.ui import MainWindow
    except ImportError as exc:
        print(f"Не удалось загрузить интерфейс: {exc}\nВыполните uv sync, затем uv run python main.py", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setApplicationName("Algo Lab")
    app.setOrganizationName("AlgoVizPrototype")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
