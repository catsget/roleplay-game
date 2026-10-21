"""Предметы игры (models/item.py из Плана.txt)."""

from dataclasses import dataclass
from enum import Enum


class ItemType(str, Enum):
    """Тип предмета (см. каталог data/)."""

    DRUG = "товар"           # запрещённый товар для торговли
    WEAPON = "оружие"
    ARMOR = "броня"
    GEAR = "снаряжение"


class DrinkQuality(str, Enum):
    """Качество партии товара (влияет на цену)."""

    LOW = "жёстокая примесь"
    NORMAL = "обычная"
    HIGH = "чистая"


@dataclass
class Item:
    """Универсальный предмет. Товары описаны в data/drugs_data.py."""

    item_id: str
    name: str
    type: ItemType
    base_price: int        # средняя цена за единицу, ₽
    weight: float          # вес единицы, кг (для вместимости)

    # только для товаров:
    price_min_pct: float = 0.5   # минимальная доля от базовой цены
    price_max_pct: float = 1.6   # максимальная доля
    heat_gain: int = 0           # прирост розыска при обыске с этим товаром

    def price_range(self) -> tuple:
        """Диапазон цен в игровом магазине: (минимум, максимум)."""
        return (int(self.base_price * self.price_min_pct),
                int(self.base_price * self.price_max_pct))
