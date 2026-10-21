"""Мир игры (models/world.py из Плана.txt): день, районы, будущие фракции."""

from typing import Optional

# В M1 районы жёстко заданы; в M2+ переедут в data/districts_data.py
DISTRICT_NAMES = ("Центральный", "Северный", "Южный", "Восточный", "Западный")


class World:
    """Состояние мира: счёт дней и районы города."""

    def __init__(self) -> None:
        self.day: int = 1                       # текущий день забега
        self.district_names: tuple = DISTRICT_NAMES
        # словарь район -> имя фракции-владельца ("" = ничья земля). М7+.
        self.district_owner: dict = {name: "" for name in DISTRICT_NAMES}
        # день, до которого нужно погасить стартовый долг
        self.debt_deadline: int = 0             # выставляется при новой игре

    @property
    def controlled_districts(self) -> int:
        """Сколько районов контролирует игрок (владелец = 'Игрок')."""
        return sum(1 for owner in self.district_owner.values() if owner == "Игрок")

    def next_day(self) -> None:
        self.day += 1

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "district_owner": dict(self.district_owner),
            "debt_deadline": self.debt_deadline,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        world = cls()
        world.day = data["day"]
        owners = data.get("district_owner", {})
        world.district_owner = {name: owners.get(name, "") for name in world.district_names}
        world.debt_deadline = data.get("debt_deadline", 0)
        return world
