#!/bin/sh
cd "$(dirname "$0")" || exit 1
PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export PATH
if ! command -v uv >/dev/null 2>&1; then
    printf '%s\n' 'Не найден uv. На macOS выполните: brew install uv' 'Затем запустите этот файл ещё раз. Инструкция: README.md'
    read -r unused_input
    exit 1
fi
uv run "$@" python main.py
result=$?
if [ "$result" -ne 0 ]; then
    printf '%s\n' 'Запуск завершился с ошибкой. Смотрите README.md. Нажмите Enter.'
    read -r unused_input
fi
exit "$result"
