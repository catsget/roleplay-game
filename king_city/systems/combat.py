"""Боевка (systems/combat.py из Плана.txt): автосимуляция с текстовым логом.

Функция simulate_fight получает участников и возвращает (журнал, итог).
UI печатает журнал целиком. Модели живут в данных, никуда не печатают.
"""

import dataclasses
from dataclasses import dataclass, field

from king_city.core.rng import Rng

WEAPON_NAME_DEFAULT = "кулаки"


@dataclass
class Fighter:
    """Участник драки: игрок или его противник."""

    name: str
    strength: int         # сила: урон
    agility: int          # ловкость: попадание/уклонение
    endurance: int        # выносливость: терпимость к боли (+HP)
    hp: int
    weapon: str = "Кулаки"      # имя оружия (для лога)
    weapon_mult: float = 0.8    # множитель урона
    weapon_accuracy: float = 0.0  # бонус к точности
    armor_prc: int = 0          # защита бронёй в процентах
    is_player: bool = False
    # состояние
    stunned: int = 0            # оглушение: пропускает ходов
    fled: bool = False
    died: bool = False

    @property
    def max_hp(self) -> int:
        return self.hp  # упрощение: HP даётся уже с выносливостью

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.fled


@dataclass
class FightResult:
    """Итог драки."""

    log: list = field(default_factory=list)   # строки-события
    winner: str = ""
    player_hp_after: int = 0
    player_survived: bool = True
    loot_money: int = 0                      # сколько поднял с побеждённого

    def append(self, line: str) -> None:
        self.log.append(line)


def simulate_fight(player: Fighter, enemy: Fighter, rng: Rng,
                   can_flee: bool = True) -> FightResult:
    """Автосимуляция пошаговой драки. Возвращает журнал и результат."""
    result = FightResult(player_hp_after=player.hp)
    result.append(f"— ДРАКА: {player.name} против {enemy.name} —")
    result.append(f"  {player.name}: HP {player.hp}, {player.weapon}.")
    result.append(f"  {enemy.name}: HP {enemy.hp}, {enemy.weapon}.")

    turn = 0
    while player.alive and enemy.alive:
        turn += 1
        if turn >= 20:   # страховка от бесконечных драк
            result.append("Оба разбрелись — толпа сдержала наезд.")
            break
        _attack(player, enemy, rng, result)
        if not enemy.alive or enemy.fled:
            break
        _attack(enemy, player, rng, result)

    result.player_hp_after = player.hp
    result.player_survived = player.hp > 0

    if not player.alive:
        result.winner = enemy.name
        result.append(f"{player.name} разваливается на асфальте. Конец боя.")
    elif not enemy.alive:
        result.winner = player.name
        result.append(f"{enemy.name} валяется. Бой за тобой.")
        result.loot_money = _loot_from(enemy, rng)
        if result.loot_money:
            result.append(f"Ты обшарил: +{result.loot_money} ₽.")
    elif enemy.fled:
        result.winner = player.name
        result.append(f"{enemy.name} пёрлся без оглядки.")
    else:
        result.winner = "никто"   # «толпа сдержала»

    return result


# --- шаги симуляции ---

def _attack(attacker: Fighter, defender: Fighter, rng: Rng,
            result: FightResult) -> None:
    """Атака одного бойца (учёт оглушения, побега, повесток урона)."""
    if attacker.fled or not attacker.alive:
        return
    if attacker.stunned > 0:
        attacker.stunned -= 1
        result.append(f"{attacker.name} в нокаут-качании, ходь зря.")
        return
    # попытка развалить драку: бежать может любой, раненый охотнее
    if attacker.hp < attacker.endurance and attacker.strength < 12:
        if rng.chance(0.2):
            attacker.fled = True
            result.append(f"{attacker.name} испарился с места.")
            return
    # точность: база 50% + ловкость атакующего − ловкость защищающего + оружие
    chance = (0.50 + attacker.weapon_accuracy
              + attacker.agility / 100.0 - defender.agility / 80.0)
    chance = max(0.15, min(0.9, chance))
    if not rng.chance(chance):
        result.append(f"{attacker.name} промахнулся по {defender.name}.")
        return
    # урон: сила × оружие ± разброс; броня режет
    dmg = attacker.strength * attacker.weapon_mult * rng.roll_float(0.8, 1.3)
    if defender.armor_prc:
        dmg *= (1.0 - defender.armor_prc / 100.0)
    dmg = max(1, int(dmg))
    defender.hp -= dmg
    result.append(
        f"{attacker.name} вмазал {defender.name}: −{dmg} "
        f"(осталось {max(0, defender.hp)}).")
    # крит: редко — оглушение
    if rng.chance(0.08):
        defender.stunned = 1
        result.append(f"{defender.name} уплыл в сработ — оглушён.")


def _loot_from(enemy: Fighter, rng: Rng) -> int:
    """Сколько подъёма с побеждённого NPC."""
    return rng.roll(0, 60 + enemy.endurance * 8) if not enemy.is_player else 0


# --- сборщики бойцов ---

def fighter_from_player(player, weapon: dict | None) -> Fighter:
    """Создаёт Fighter из моделей Player (+ оружие из data/weapons_data)."""
    w = weapon or {}
    return Fighter(
        name=player.name,
        strength=player.stats.strength,
        agility=player.stats.agility,
        endurance=player.stats.endurance,
        hp=player.hp,
        weapon=w.get("name", "Кулаки"),
        weapon_mult=w.get("dmg_mult", 0.8),
        weapon_accuracy=w.get("accuracy", 0.0),
        armor_prc=w.get("armor_prc", 0),
        is_player=True,
    )


def fighter_npc(name: str, day: int, rng: Rng) -> Fighter:
    """Случайный уличный тип; сила растёт с днём города."""
    from king_city.data.weapons_data import WEAPON_ORDER, WEAPONS
    base = 8 + min(day // 30, 8)          # +1 сила за каждые 30 дней
    weapon = WEAPONS["fists"]
    if rng.chance(0.25 + day / 1000):
        weapon = WEAPONS[rng.choice(
            [wid for wid in WEAPON_ORDER if wid != "fists"])]
    return Fighter(
        name=name,
        strength=base + rng.roll(-2, 3),
        agility=base + rng.roll(-2, 2),
        endurance=base + rng.roll(0, 2),
        hp=28 + rng.roll(0, 10) + min(day // 20, 15),
        weapon=weapon["name"],
        weapon_mult=weapon["dmg_mult"],
        weapon_accuracy=weapon["accuracy"],
        armor_prc=npc_armor(rng, day),
    )


def npc_armor(rng: Rng, day: int) -> int:
    """Шанс на кожанку у NPC (бронижилет — с ростом дня)."""
    from king_city.data.armors_data import ARMORS
    if day > 100 and rng.chance(0.1):
        return ARMORS["vest"]["protection"]
    if rng.chance(0.35):
        return ARMORS["jacket"]["protection"]
    return 0
