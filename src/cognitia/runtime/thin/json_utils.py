"""Утилиты для извлечения JSON-объектов из произвольного текста.

find_json_object_boundaries — единственная точка brace-tracking логики.
Используется StreamParser и ThinRuntime вместо дублированных реализаций.
"""

from __future__ import annotations


def find_json_object_boundaries(text: str, start: int = 0) -> tuple[int, int] | None:
    """Найти границы первого полного JSON-объекта ({...}) в тексте.

    Отслеживает вложенность фигурных скобок, строковые литералы
    и escaped-символы. Не выполняет json.loads — только определяет
    позиции начала и конца сбалансированного объекта.

    Args:
        text: Текст для поиска.
        start: Позиция, с которой начинать поиск (по умолчанию 0).

    Returns:
        Кортеж (start, end) где text[start:end] — полный JSON-объект,
        или None если сбалансированный объект не найден.
    """
    obj_start = text.find("{", start)
    if obj_start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for idx in range(obj_start, len(text)):
        ch = text[idx]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return (obj_start, idx + 1)

    return None
