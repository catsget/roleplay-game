"""Генерация рыночных цен (systems/economy.py из Плана.txt).

Цены зависят от товара (база + диапазон), от района (множители закупки/
продажи) и от дня: к концу года инфляция толкает цены вверх (~+25%).
События-модификаторы («облава», «большая партия») добавляются в M9.
"""

import math
from typing import Dict, Tuple

from king_city.core.rng import Rng
from king_city.data.drugs_data import DRUG_ORDER, build_drugs
from king_city.data.districts_data import DISTRICT_ORDER, districts_as_dicts
from king_city.settings import DAYS_TOTAL

DRUGS = build_drugs()
DISTRICTS = districts_as_dicts()


class Economy:
    """Управляет ценами всех районов на текущий день.

    Цены хранятся как {district_id: {item_id: (цена_закупки, цена_продажи)}}.
    """

    def __init__(self, rng: Rng) -> None:
        self.rng = rng
        self.prices: Dict[str, Dict[str, Tuple[int, int]]] = {}

    # --- генерация ---

    def regenerate(self, day: int) -> None:
        """Сгенерировать цены нового дня для всех районов (раз в день)."""
        t = min(1.0, day / DAYS_TOTAL)     # прогресс года
        inflation = 1.0 + 0.25 * t
        self.prices = {
            district_id: {
                item_id: self._price(item_id, district_id, inflation)
                for item_id in DRUG_ORDER
            }
            for district_id in DISTRICT_ORDER
        }

    def _price(self, item_id: str, district_id: str,
               inflation: float) -> Tuple[int, int]:
        item = DRUGS[item_id]
        district = DISTRICTS[district_id]
        low, high = item.price_range()
        raw = self.rng.roll(low, high)
        buy = raw * district["price_buy_mult"] * inflation
        sell = raw * district["price_sell_mult"] * inflation
        return self._round5(int(buy)), self._round5(int(sell))

    @staticmethod
    def _round5(value: int) -> int:
        """Округление до 5 ₽ (уличные цены всегда кратны пятерке)."""
        return max(5, int(math.floor(value / 5)) * 5)

    # --- доступ ---

    def buy_price(self, district_id: str, item_id: str) -> int:
        return self.prices[district_id][item_id][0]

    def sell_price(self, district_id: str, item_id: str) -> int:
        return self.prices[district_id][item_id][1]

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {"prices": self.prices}

    def load_dict(self, data: dict) -> None:
        self.prices = data.get("prices", {})
