"""Smoke-тест M6: разведка цели, ограбление, чёрный рынок железа.

Запуск: python king_city/tests/test_smoke_heist.py
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import king_city.core.console_ui as console_ui


def run_script(script: str, seed: int, boost: bool = False) -> tuple:
    """Возвращает (вывод, ссылку на объект Game для инспекции)."""
    from king_city.core.game import Game
    ui = console_ui.ConsoleUI()
    game = Game(ui)
    game.rng.reseed(seed)
    in_backup, out_backup = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(script)
    sys.stdout = buffer = io.StringIO()
    try:
        game.run()
    finally:
        sys.stdin, sys.stdout = in_backup, out_backup
    return buffer.getvalue(), game


def check(out: str, token: str, what: str, failed: list) -> None:
    if token in out:
        print(f"  [OK] {what}")
    else:
        print(f"  [ПРОВАЛ] {what} (нет «{token}»)")
        failed.append(what)


def main() -> int:
    print("Тест 1: разведка и ограбление киоска (стартовая репа)")
    # 1; Тест; ""; 4 (ограбление); 1 (киоск); 1 (разведка); 2 (погнали); 0; 0 (спать); 3
    out, game = run_script("1\nТест\n\n4\n1\n1\n2\n0\n0\n3\n", seed=11)
    failed = []
    check(out, "ДЕЛО", "ограбление началось", failed)
    check(out, "Успех", "дело закрылось деньгами/разводкой результата", failed)

    print("Тест 2: чёрный рынок — покупка кастета (300 ₽)")
    # 7 (связи); 3 (рынок); 1 (кастет); 0 (назад); 0 (спать); 3
    out, game = run_script("1\nТест\n\n7\n3\n1\n0\n0\n3\n", seed=5)
    check(out, "твоё", "оружие экипировано", failed)
    state = game.saves.load_autosave()
    if state and state["player"]["money"] == 200:
        print(f"  [OK] сняты деньги (в сейве {state['player']['money']} ₽)")
    else:
        print(f"  [ПРОВАЛ] деньги не снялись корректно: "
              f"{None if not state else state['player']['money']}")
        failed.append("деньги на рынке")

    print("=" * 60)
    if failed:
        print(f"ИТОГ: ПРОВАЛЫ: {failed}")
        return 1
    print("ИТОГ: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
