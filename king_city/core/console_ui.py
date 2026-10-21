"""Консольный интерфейс для Windows/Linux (см. раздел 8 Плана.txt).

Единственное место в проекте, где разрешены print и input.
Цвета — через ANSI-коды, поддержка включается на Windows через os.system("").
"""

import os
import sys
import time
from typing import Iterable, Optional, Sequence, Tuple

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"

WIDTH = 68  # ширина текстовой зоны


def _enable_windows_vt() -> None:
    """Включает обработку ANSI на Windows и UTF-8 кодировку вывода."""
    if os.name == "nt":
        os.system("")  # активирует VT-обработку в консоли
        os.system("chcp 65001 >nul")  # таблица символов UTF-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # не Windows или старый Python — работаем как есть


class ConsoleUI:
    """Все консольный ввод-вывод игры."""

    def __init__(self, slow_time: float = 0.015) -> None:
        _enable_windows_vt()
        self.slow_time = slow_time

    # --- примитивы печати ---

    def print_line(self, text: str = "", color: str = "", end: str = "\n") -> None:
        """Печать строки одним куском (мгновенно)."""
        prefix = color if color else ""
        sys.stdout.write(f"{prefix}{text}{RESET if prefix else ''}{end}")

    def slow(self, text: str = "", color: str = "", end: str = "\n") -> None:
        """Печать посимвольно (для атмосферных моментов: бой, эпилоги)."""
        if color:
            sys.stdout.write(color)
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            if self.slow_time > 0:
                time.sleep(self.slow_time)
        sys.stdout.write(f"{RESET}{end}")
        sys.stdout.flush()

    def divider(self, char: str = "─") -> None:
        """Горизонтальная линия."""
        self.print_line(char * WIDTH, DIM)

    def header(self, title: str) -> None:
        """Заголовок экрана: линия + центрированный текст + линия."""
        self.clear()
        self.divider()
        self.print_line(f"{title:^{WIDTH}}", BOLD)
        self.divider()

    def bar(self, label: str, value: int, maximum: int, width: int = 20,
            color: str = "") -> None:
        """Полоска ресурса:  HP     [██████──────] 60/100."""
        filled = int(width * value / maximum)
        filled = max(0, min(width, filled))
        visual = "█" * filled + "─" * (width - filled)
        self.print_line(f"{label:<12}[{visual}] {value}/{maximum}", color)

    # --- ввод ---

    def ask(self, prompt: str = "> ") -> str:
        """Запрос строки; пустой ввод не проходит."""
        while True:
            answer = input(f"{prompt}").strip()
            if answer:
                return answer
            self.print_line("Введите что-нибудь.", YELLOW, end="\n")

    def ask_number(self, prompt: str, low: int, high: int) -> int:
        """Запрос числа в диапазоне с защитой от мусора.
        Повторный закрытый ввод (EOF) пробрасывается вверх — ловится на уровне цикла."""
        while True:
            try:
                value = int(input(f"{prompt}").strip())
            except ValueError:
                self.print_line("Введите число.", YELLOW)
                continue
            if low <= value <= high:
                return value
            self.print_line(f"Число должно быть от {low} до {high}.", YELLOW)

    def menu(self, title: str, options: Sequence[Tuple[str, str]]) -> str:
        """Меню с произвольными ключами.

        options = [(ключ, подпись), ...] например [("1", "Торговля"), ("0", "Спать")].
        Возвращает выбранный ключ (str). Неверный ввод повторяет вопрос.
        """
        self.header(title)
        for key, label in options:
            self.print_line(f"  [{key}] {label}")
        self.divider()
        valid = {key for key, _ in options}
        while True:
            answer = input("> ").strip()
            if answer in valid:
                return answer
            self.print_line("Такого пункта нет. Смотри список выше.", YELLOW)

    def pause(self, prompt: str = "\n<Enter> — продолжить") -> None:
        """Пауза до нажатия Enter; молча продолжает даже при Ctrl+C-подобном вводе."""
        try:
            input(prompt)
        except EOFError:
            pass

    def clear(self) -> None:
        """Очистка экрана."""
        os.system("cls" if os.name == "nt" else "clear")

    # --- таблица персонажа ---

    def character_panel(self, description: Iterable[Tuple[str, str, str]]) -> None:
        """Печать одинаковых строк вида «имя ..... значение».

        description = [(подпись, значение, цвет), ...].
        """
        for label, value, color in description:
            self.print_line(f"  {label:<12} {value}", color)
