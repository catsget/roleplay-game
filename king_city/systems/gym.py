"""Спортзал и прокачка статов (systems/gym.py из Плана.txt).

Занятие стоит энергии и слота. Отдача +1..2 к стату; после порога 40 —
убывающая отдача (+1 за каждое второе занятие, счётчик у стата).
Перетренировка при нехватке энергии бьёт по HP.
"""

from king_city.core.console_ui import GREEN, RED, YELLOW, ConsoleUI
from king_city.core.rng import Rng
from king_city.models.player import Player

# id, название, стат, цена ₽, энергия, описание
GYM_ACTIVITIES = [
    ("bars",  "Турник во дворе",    "strength",     0,   30,
     "Бесплатно и бесконечно. Руки затекают, зато без взноса."),
    ("iron",  "Качалка «Титан»",    "strength",     200, 35,
     "Штанга, тренер, полотенце. Сила растёт заметно."),
    ("round", "Ринг в подвале",     "agility",      300, 35,
     "Пропаренный воздух, перчатки. Ловкость плюс синяки."),
    ("run",   "Бег по набережной",  "endurance",    0,   30,
     "Соревнование с самим собой и трамваем."),
    ("books", "Книжный «Магеллан»", "intelligence", 150, 25,
     "Стол, лампа, конспект. Интеллект от чтения."),
    ("bar",   "Бар «Стопор»",       "charisma",     250, 25,
     "Сказки за стойкой. Харизма от практики болтовни."),
]

STAT_NAMES = {
    "strength": "Сила",
    "agility": "Ловкость",
    "charisma": "Харизма",
    "intelligence": "Интеллект",
    "endurance": "Выносливость",
}

SOFT_CAP = 40             # после 40 идёт убывающая отдача
OVERTRAIN_HP_COST = 5     # заряд HP за перетренировку
STAT_GAIN_MAX = 2         # базовый прирост


class Gym:
    """Прокачка статов через занятия."""

    def __init__(self, ui: ConsoleUI, rng: Rng, actions) -> None:
        self.ui = ui
        self.rng = rng
        self.actions = actions      # менеджер слотов дня (systems/actions.py)
        # счётчики занятий по статам с порога: {"strength": 0, ...}
        self.soft_counters: dict = {name: 0 for name in STAT_NAMES}

    # --- экраны ---

    def gym_screen(self, player: Player) -> None:
        self.ui.header("СПОРТЗАЛ")
        while True:
            options = []
            for index, (act_id, name, stat, cost, energy, desc) in enumerate(
                    GYM_ACTIVITIES, start=1):
                price = f"₽{cost}" if cost else "бесплатно"
                options.append((str(index), f"{name} ({STAT_NAMES[stat]}, {price})"))
            options.append(("0", "Назад"))
            action = self.ui.menu("Что тренируем?", options)
            if action == "0":
                return
            self.train(player, GYM_ACTIVITIES[int(action) - 1])

    # --- механика ---

    def train(self, player: Player, activity: tuple) -> None:
        act_id, name, stat, cost, energy, desc = activity
        if not self.actions.has_slots():
            self.ui.print_line("День уже расписан — время спать.", YELLOW)
            return
        if player.energy < energy:
            # перетренировка: из последних сил, ценой HP
            if player.energy <= 0:
                self.ui.print_line(f"Перетренировка! Нет сил на «{name}».", RED)
                return
            self.ui.print_line("Ты пашешь на последних силах…", YELLOW)
            player.hurt(OVERTRAIN_HP_COST)
        if cost > 0 and not player.spend(cost):
            self.ui.print_line(f"Не хватает {cost - player.money} ₽ на «{name}».",
                               RED)
            return
        self.actions.use_slot()
        player.energy = max(0, player.energy - energy)
        gained = self.stat_gain(player, stat)
        old = getattr(player.stats, stat)
        # сила наращивает вместимость рюкзака
        player.inventory.set_strength(player.stats.strength)
        self.ui.print_line(
            f"  «{name}»: {STAT_NAMES[stat]} {old} → {old + gained} "
            f"({player.money} ₽, энергия {player.energy}).", GREEN)

    def stat_gain(self, player: Player, stat: str) -> int:
        """Прирост стата с убывающей отдачей после SOFT_CAP."""
        current = getattr(player.stats, stat)
        if current < SOFT_CAP:
            return player.stats.increase(stat, self.rng.roll(1, STAT_GAIN_MAX))
        index = self.soft_counters[stat] = self.soft_counters.get(stat, 0) + 1
        if index % 2:   # нечётное занятие за порогом — прироста нет
            self.ui.print_line("  Стены упёрлись: дальше только упорством.", YELLOW)
            return 0
        return player.stats.increase(stat, 1)
