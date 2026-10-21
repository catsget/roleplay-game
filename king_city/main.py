"""Точка входа игры «Король города».

Запуск: python main.py из папки king_city (или python -m king_city.main из корня).
"""

import os
import sys

# Позволяем запускать main.py напрямую: кладём корень проекта в sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from king_city.core.console_ui import ConsoleUI
from king_city.core.game import Game


def main() -> None:
    ui = ConsoleUI()
    game = Game(ui)
    game.run()


if __name__ == "__main__":
    main()
