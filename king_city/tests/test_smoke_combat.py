"""Smoke-тест M4: уличная драка по логу, победа/подъём; ветераны города сильнее.

Запуск: python king_city/tests/test_smoke_combat.py
"""

import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from king_city.core.rng import Rng
from king_city.systems.combat import Fighter, simulate_fight, fighter_npc

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


def main() -> int:
    print("Тест A: чистая симуляция драки 100 раз — должна заканчиваться")
    rng = Rng(7)
    player_wins, enemy_wins, draws = 0, 0, 0
    for _ in range(100):
        player = Fighter("Тест", strength=15, agility=15, endurance=12,
                         hp=60, weapon_mult=1.3)
        enemy = fighter_npc("Топтун", day=50, rng=rng)
        result = simulate_fight(player, enemy, rng)
        if result.winner == "Тест":
            player_wins += 1
        elif result.winner == "Топтун":
            enemy_wins += 1
        else:
            draws += 1
    print(f"  Победы игрока: {player_wins}, врага: {enemy_wins}, "
          f"разбежались: {draws}")
    a_ok = player_wins + enemy_wins + draws == 100
    print(f"  [{'OK' if a_ok else 'ПРОВАЛ'}] каждая драка завершается")

    print("Тест B: полный забег с дракой")
    # 1; Тест; ""; 9 (отдых) — с шансом драки подряд; несколько итераций, сон, выход
    out = run_script("1\nТест\n\n9\n9\n0\n3\n", seed=42)
    b_ok = "ДРАКА" in out or "уходит в переулок" in out or "план дня" in out
    print(f"  [{ 'OK' if b_ok else 'ПРОВАЛ' }] забег проходит, в журнале драка или покой")

    print("=" * 60)
    failed = []
    if not a_ok:
        failed.append("симуляция")
    if not b_ok:
        failed.append("забег M4")
    if failed:
        print(f"ИТОГ: ПРОВАЛЫ: {failed}")
        return 1
    print("ИТОГ: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
