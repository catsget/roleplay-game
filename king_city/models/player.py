"""Игрок — центральная сущность (models/player.py из Плана.txt).

Только данные и простые операции над ними. Ввод-вывод — через core/console_ui.
"""

from typing import Optional

from king_city.models.inventory import Inventory
from king_city.models.item import Item
from king_city.models.stats import Stats
from king_city.settings import (DEBT_INTEREST, HEAT_DECAY, HEAT_MAX, MAX_HP,
                                WIN_REPUTATION)


class Player:
    """Состояние персонажа игрока."""

    def __init__(self, name: str, stats: Optional[Stats] = None) -> None:
        self.name: str = name
        self.stats: Stats = stats if stats is not None else Stats()
        self.inventory = Inventory(strength=self.stats.strength)
        self.money: int = 0          # наличные, ₽
        self.debt: int = 0           # долг кредиторам, ₽
        self.hp: int = MAX_HP
        self.max_hp: int = MAX_HP
        self.energy: int = 0         # перезаписывается сном (энергия на день)
        self.heat: int = 0           # розыск 0..100
        self.reputation: int = 0     # репутация 0..1000
        # --- трудоустройство (M3) ---
        self.job_id: str | None = None   # None = безработный
        self.job_shifts: int = 0         # отработано смен на текущей работе
        self.job_level: int = 0          # уровень должности (0..4), растёт от стажа
        self.days_worked_legally: int = 0  # для будущего алиби и спада heat
        self.kills: int = 0          # статистика забега
        self.arrests: int = 0        # статистика забега (сколько раз сажали)
        # --- снаряжение (M4): магазин оружия — в M6+ ---
        self.equipped_weapon: dict = {"id": "fists", "name": "Кулаки",
                                      "dmg_mult": 0.8, "accuracy": 0.0}
        self.equipped_armor: dict = {}   # пусто — без брони

    # --- деньги ---

    def add_money(self, amount: int) -> None:
        """Изменить наличные в любую сторону."""
        self.money += amount
        if self.money < 0:  # страховка: в долг через деньги не уводим
            self.money = 0

    def can_spend(self, amount: int) -> bool:
        return self.money >= amount

    def spend(self, amount: int) -> bool:
        """Потратить деньги; False, если их не хватает."""
        if not self.can_spend(amount):
            return False
        self.money -= amount
        return True

    def take_loan(self, amount: int) -> None:
        """Взять в долг у кредиторов."""
        self.money += amount
        self.debt += amount

    def pay_debt(self, amount: int) -> int:
        """Погасить часть долга; возвращает фактически уплаченное."""
        payment = min(amount, self.debt, self.money)
        self.money -= payment
        self.debt -= payment
        return payment

    def accrue_interest(self) -> int:
        """Начислить проценты по долгу. Возвращает начисленную сумму."""
        if self.debt <= 0:
            return 0
        interest = max(1, int(self.debt * DEBT_INTEREST))
        self.debt += interest
        return interest

    # --- здоровье ---

    def is_alive(self) -> bool:
        return self.hp > 0

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def hurt(self, amount: int) -> None:
        """Получение урона (может убить — проверка в is_alive())."""
        self.hp = max(0, self.hp - amount)

    # --- полиция и репутация ---

    def add_heat(self, amount: int) -> None:
        self.heat = max(0, min(HEAT_MAX, self.heat + amount))

    def reduce_heat(self, amount: int) -> None:
        self.heat = max(0, self.heat - amount)

    def add_reputation(self, amount: int) -> None:
        self.reputation = max(0, min(WIN_REPUTATION, self.reputation + amount))

    # --- сериализация ---

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "stats": self.stats.to_dict(),
            "inventory": self.inventory.to_dict(),
            "money": self.money,
            "debt": self.debt,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "energy": self.energy,
            "heat": self.heat,
            "reputation": self.reputation,
            "job_id": self.job_id,
            "job_shifts": self.job_shifts,
            "job_level": self.job_level,
            "days_worked_legally": self.days_worked_legally,
            "kills": self.kills,
            "arrests": self.arrests,
            "equipped_weapon": dict(self.equipped_weapon),
            "equipped_armor": dict(self.equipped_armor),
        }

    @classmethod
    def from_dict(cls, data: dict, catalog: Optional[dict] = None) -> "Player":
        player = cls(data["name"], Stats.from_dict(data["stats"]))
        if catalog:
            for item in catalog.values():
                player.inventory.register(item)
        player.inventory.load_dict(data.get("inventory", {}))
        player.money = data["money"]
        player.debt = data["debt"]
        player.hp = data["hp"]
        player.max_hp = data["max_hp"]
        player.energy = data["energy"]
        player.heat = data["heat"]
        player.reputation = data["reputation"]
        player.job_id = data.get("job_id")
        player.job_shifts = data.get("job_shifts", 0)
        player.job_level = data.get("job_level", 0)
        player.days_worked_legally = data["days_worked_legally"]
        player.kills = data["kills"]
        player.arrests = data["arrests"]
        player.equipped_weapon = data.get("equipped_weapon",
                                          {"id": "fists", "name": "Кулаки",
                                           "dmg_mult": 0.8, "accuracy": 0.0})
        player.equipped_armor = data.get("equipped_armor", {})
        return player
