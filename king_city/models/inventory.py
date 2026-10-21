"""Комплект Player: инвентарь (models/inventory.py из Плана.txt).

Хранит товары (имя -> количество) и прочие предметы. Вес ограничен
«сила x коэффициент + снаряжение».
"""

from typing import Dict, Optional

from king_city.models.item import Item, ItemType

BASE_CAPACITY_PER_STRENGTH = 3.0   # кг веса на единицу силы


class CapacityError(Exception):
    """Попытка уложить в рюкзак больше, чем поднимает игрок."""


class Inventory:
    """Инвентарь игрока с ограничением по весу."""

    def __init__(self, strength: int = 10, extra_capacity: float = 0.0) -> None:
        self._items: Dict[str, int] = {}   # item_id -> количество
        self._catalog: Dict[str, Item] = {}
        self.strength = strength
        self.extra_capacity = extra_capacity   # рюкзаки/машина добавляют вместимость

    # --- вместимость ---

    @property
    def capacity(self) -> float:
        return self.strength * BASE_CAPACITY_PER_STRENGTH + self.extra_capacity

    @property
    def used(self) -> float:
        return sum(
            item.weight * count
            for item, count in zip(self._catalog.values(), self._items.values())
        ) if self._catalog else 0.0

    @property
    def free(self) -> float:
        return max(0.0, self.capacity - self.used)

    # --- хранение ---

    def register(self, item: Item) -> None:
        """Зарегистрировать тип предмета (при старте игры из data/)."""
        self._catalog[item.item_id] = item

    def add(self, item_id: str, count: int) -> int:
        """Добавить товар; вернуть сколько реально уложилось.

        Бросает CapacityError, если не влезает даже одна единица.
        """
        if item_id not in self._catalog:
            raise KeyError(f"Неизвестный предмет: {item_id}")
        item = self._catalog[item_id]
        fits = int(self.free // item.weight) if item.weight > 0 else count
        placed = min(count, fits)
        if placed <= 0:
            raise CapacityError("Не поднимаешь столько.")
        self._items[item_id] = self._items.get(item_id, 0) + placed
        return placed

    def remove(self, item_id: str, count: int) -> int:
        """Изъять товар; вернуть сколько реально изъято."""
        have = self._items.get(item_id, 0)
        taken = min(count, have)
        if taken > 0:
            self._items[item_id] = have - taken
            if self._items[item_id] == 0:
                del self._items[item_id]
        return taken

    def count(self, item_id: str) -> int:
        return self._items.get(item_id, 0)

    def items(self) -> dict:
        """Видимая часть инвентаря: {item_id: количество}."""
        return dict(self._items)

    def item(self, item_id: str) -> Optional[Item]:
        return self._catalog.get(item_id)

    def total_heat_gain(self) -> int:
        """Суммарный прирост розыска, если копы обыщут инвентарь."""
        total = 0
        for item_id, count in self._items.items():
            item = self._catalog.get(item_id)
            if item and item.type == ItemType.DRUG:
                total += item.heat_gain * count
        return int(total)

    def set_strength(self, strength: int) -> None:
        self.strength = strength

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {
            "strength": self.strength,
            "extra_capacity": self.extra_capacity,
            "items": dict(self._items),
        }

    def load_dict(self, data: dict) -> None:
        self.strength = data["strength"]
        self.extra_capacity = data.get("extra_capacity", 0.0)
        self._items = {key: value for key, value in data.get("items", {}).items()
                       if value > 0}
