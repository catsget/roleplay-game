"""Smoke-тест M2: новая игра → купил товар → спать → новый день.

Запуск: python king_city/tests/test_smoke_trading.py
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
    """Прогоняет скрипт ввода через игру в памяти."""
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


def main() -> int:
    print("Тест 1: покупка товара на рынке Южного")
    out = run_script("1\nТест\n\n1\n3\n1\n1\n1\n0\n0\n3\n")
    checks = [
        ("РЫНОК", "рынок открылся"),
        ("Купил", "покупка прошла"),
        ("Утро дня 2", "день сменился"),
    ]
    failed = []
    for token, what in checks:
        if token in out:
            print(f"  [OK] {what}")
        else:
            print(f"  [ПРОВАЛ] {what}: нет «{token}»")
            failed.append(what)

    print("Тест 2: загрузка автосохранения")
    out2 = run_script("2\n\n0\n3\n")
    if "Завалился" in out2 or "Утро дня" in out2:
        print("  [OK] сейв загрузился")
    else:
        print("  [ПРОВАЛ] автосохранение не грузится")
        failed.append("автосохранение")

    print("=" * 60)
    if failed:
        print(f"ИТОГ: ПРОВАЛЫ: {failed}")
        return 1
    print("ИТОГ: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
