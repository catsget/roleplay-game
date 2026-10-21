"""Характеристики игрока (раздел 4 Плана.txt)."""

from dataclasses import dataclass


@dataclass
class Stats:
    """Пять базовых характеристик. Всё остальное в игре считается от них."""

    strength: int = 10        # сила: урон в драке, переносимый вес
    agility: int = 10         # ловкость: уклонение, побеги, ограбления
    charisma: int = 10        # харизма: торг, найм, отношения
    intelligence: int = 10    # интеллект: разведка, схемы, апгрейды
    endurance: int = 10       # выносливость: запас энергии, живучесть

    MIN_STAT = 1
    MAX_STAT = 100

    def to_dict(self) -> dict:
        return {
            "strength": self.strength,
            "agility": self.agility,
            "charisma": self.charisma,
            "intelligence": self.intelligence,
            "endurance": self.endurance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Stats":
        return cls(
            strength=data["strength"],
            agility=data["agility"],
            charisma=data["charisma"],
            intelligence=data["intelligence"],
            endurance=data["endurance"],
        )

    def increase(self, name: str, amount: int) -> int:
        """Поднять стат с ограничениями; возвращает фактический прирост."""
        if not hasattr(self, name):
            raise KeyError(f"Неизвестная характеристика: {name}")
        current = getattr(self, name)
        target = current + amount
        raised = max(self.MIN_STAT, min(self.MAX_STAT, target)) - current
        setattr(self, name, current + raised)
        return raised

    def totals(self) -> int:
        """Сумма всех статов (для оценки силы игрока в бою)."""
        return (self.strength + self.agility + self.charisma
                + self.intelligence + self.endurance)
