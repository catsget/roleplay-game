"""Smoke-тест M5: полиция — взятка копам, долг, суд и отсидка единичной силы.

Запуск: python king_city/tests/test_smoke_police.py
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import king_city.core.console_ui as console_ui


def run_script(script: str, seed: int) -> str:
    from king_city.core.game import Game
    ui = console_ui.ConsoleUI()
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
    print("Тест 1: связи и взятки (гасим долг с 1030 ₽)")
    # 1; Тест; ""; 7 (связи); 2 (погасить долг); 500 (лимит — карман 500); 0; 0; 3
    out = run_script("1\nТест\n\n7\n2\n500\n0\n0\n3\n", seed=5)
    failed = []
    check(out, "Погасил", "погашение долга работало", failed)

    print("Тест 2: суд и отсидка — прямой запуск без консоли")
    from king_city.core.game import Game
    from king_city.models.player import Player
    from king_city.models.world import World
    from king_city.models.prison import Prison
    ui = console_ui.ConsoleUI()
    game = Game(ui)
    game.rng.reseed(9)
    inp_backup, out_backup = sys.stdin, sys.stdout
    try:
        sys.stdin = io.StringIO("")
        sys.stdout = buffer = io.StringIO()
        game.player = Player("Зек")
        game.world = World()
        player = game.player
        player.heat = 60
        game.current_sentence = 5
        Prison.serve(player, game, game.rng)   # день 3-й предложит побег — ввод пуст → отказ? 
        # ВАЖНО: тут меню может ронять IOS EOF... проверяем результат после
        sys.stdout = sys.__stdout__
        sys.stdin = inp_backup
        result = buffer.getvalue()
        ok = "Тебя выпустили" in result or player.hp <= 0
        print(f"  [{'OK' if ok else 'ПРОВАЛ'}] отсидка завершилась "
              f"(HP игрока: {player.hp}, heat после: {player.heat})")
        if not ok:
            failed.append("отсидка")
    finally:
        sys.stdin, sys.stdout = inp_backup, out_backup

    print("=" * 60)
    if failed:
        print(f"ИТОГ: ПРОВАЛЫ: {failed}")
        return 1
    print("ИТОГ: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
