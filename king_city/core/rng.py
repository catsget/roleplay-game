"""Обёртка над random с единым seed.

Все случайные события в игре должны идти через этот класс, чтобы
забег можно было воспроизвести при отладке (см. архитектуру core/rng.py
в Плана.txt).
"""

import random
from typing import Any, Optional, Sequence


class Rng:
    """Единая точка случайности для всей игры."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def reseed(self, seed: Optional[int]) -> None:
        """Пересадить генератор на новый seed (например, при загрузке сейва)."""
        self._rng = random.Random(seed)

    def chance(self, probability: float) -> bool:
        """True с вероятностью probability (0..1)."""
        return self._rng.random() < probability

    def roll(self, low: int, high: int) -> int:
        """Случайное целое в диапазоне [low, high]."""
        return self._rng.randint(low, high)

    def roll_float(self, low: float, high: float) -> float:
        """Случайное вещественное в диапазоне [low, high]."""
        return self._rng.uniform(low, high)

    def choice(self, sequence: Sequence[Any]) -> Any:
        """Случайный элемент последовательности."""
        return self._rng.choice(sequence)

    def shuffle(self, sequence: Sequence[Any]) -> list:
        """Перемешанная копия последовательности."""
        copy = list(sequence)
        self._rng.shuffle(copy)
        return copy

    def pick_weighted(self, options: Sequence[tuple]) -> Any:
        """Взвешенный выбор: options = [(значение, вес), ...].

        Пример: pick_weighted([("простое", 70), ("редкое", 25), ("эпос", 5)]).
        """
        values = [option[0] for option in options]
        weights = [option[1] for option in options]
        return self._rng.choices(values, weights=weights, k=1)[0]
