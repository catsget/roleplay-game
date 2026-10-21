"""Smoke-тест M3: устройсь курьером → отработай смену → качалка → сон.

Запуск: python king_city/tests/test_smoke_labor.py
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from king_city.core.console_ui import ConsoleUI
from king_city.core.game import Game


def run_script(script: str, seed: int = 86) -> str:
    ui = ConsoleUI()
    game = Game(ui)
    game.rng.reseed(seed)
    in_backup, out_backup = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(script)
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        game.run()
        return buffer.getvalue()
    finally:
        sys.stdin, sys.stdout = in_backup, out_backup


def check(out: str, token: str, what: str, failed: list) -> None:
    if token in out:
        print(f"  [OK] {what}")
    else:
        print(f"  [ПРОВАЛ] {what} (нет «{token}»)")
        failed.append(what)


def main() -> int:
    print("Тест: работа курьером и спортзал")
    # 1 → новая игра; Тест; ""; 2 (работа); 1 (вакансии); 1 (курьер);
    # 0 (назад); 2 (работа); 2 (смена); 0 (назад); 3 (спортзал); 1 (турник);
    # 0 (назад); 0 (спать); 3 (выход)
    out = run_script("1\nТест\n\n2\n1\n1\n0\n2\n2\n0\n3\n1\n0\n0\n3\n")
    failed = []
    check(out, "Тебя взяли", "устройство на работу", failed)
    check(out, "Смена отработана", "смена даёт деньги", failed)
    check(out, "→", "прокачка стата", failed)
    check(out, "Утро дня 2", "день сменился", failed)

    print("=" * 60)
    if failed:
        print(f"ИТОГ: ПРОВАЛЫ: {failed}")
        return 1
    print("ИТОГ: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
