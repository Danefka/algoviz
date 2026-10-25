"""Run with the same interpreter as main.py to diagnose installation problems."""
import importlib
import platform
import sys

print("Python:", platform.python_version())
print("Interpreter:", sys.executable)
print("Platform:", platform.platform())
ok = (3, 10) <= sys.version_info < (3, 14)
if not ok:
    print("Нужен Python 3.10–3.13; проект настроен на Python 3.12.")
for name in ("PySide6",):
    try:
        module = importlib.import_module(name)
        print(name + ":", getattr(module, "__version__", "installed"))
    except Exception as exc:
        ok = False
        print(name + ": ERROR:", exc)
if "--export" in sys.argv:
    try:
        module = importlib.import_module("manim")
        print("manim:", module.__version__)
    except Exception as exc:
        ok = False
        print("manim: ERROR:", exc)
else:
    print("Manim не требуется для просмотра; проверка экспорта: --export")
print("Окружение готово." if ok else "Установите зависимости по README.md.")
raise SystemExit(0 if ok else 1)
