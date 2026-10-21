"""Меню действий дня (systems/actions.py из Плана.txt).

Ведёт план дня: слоты (3), энергия, распределение действий,
переход к «Спать». Выполняет уже реализованные системы (торговля,
работа, спортзал, отдых) и красиво отказывает на нереализованных.
"""

from king_city.core.console_ui import GREEN, YELLOW, ConsoleUI
from king_city.settings import ENERGY_PER_DAY, SLOTS_PER_DAY


class Actions:
    """Менеджер дневного цикла: слоты и действия."""

    def __init__(self, game, ui: ConsoleUI) -> None:
        self.game = game          # Game: доступ к игроку, миру и системам
        self.ui = ui

    # --- менеджмент слотов (используется другими системами) ---

    def has_slots(self) -> bool:
        return self.game.slots_used < SLOTS_PER_DAY

    def use_slot(self) -> None:
        self.game.slots_used += 1

    @property
    def slots_free(self) -> int:
        return SLOTS_PER_DAY - self.game.slots_used

    # --- дневной цикл ---

    def day_loop(self) -> str:
        """План дня до «Спать». Возвращает результат дня был для Game."""
        self.game.slots_used = 0
        from king_city.settings import DAYS_TOTAL
        while True:
            self.show_day_status()
            key = self.ui.menu(
                f"День {self.game.world.day}/{DAYS_TOTAL} — план дня", DAY_MENU)
            if key == "0":
                return self.game.finish_day()
            if key == "1":
                self.do_trading()
            elif key == "2":
                self.do_job()
            elif key == "3":
                self.do_gym()
            elif key == "9":
                self.do_rest()
            else:
                self.ui.print_line("Эта система появится в следующих обновлениях.",
                                   YELLOW)

    # --- действия ---

    def do_trading(self) -> None:
        if not self.has_slots():
            self.ui.print_line("День уже расписан — время спать.", YELLOW)
            return
        self.use_slot()
        self.game.trading.open_market(self.game.player)
        self.ui.print_line("Рынок закрылся. Слот потрачен.", YELLOW)

    def do_job(self) -> None:
        if not self.has_slots():
            self.ui.print_line("Рабочий день кончился раньше, чем ты пришёл.",
                               YELLOW)
            return
        self.game.labor.jobs_screen(self.game.player)

    def do_gym(self) -> None:
        if not self.has_slots():
            self.ui.print_line("Спортзал уже закрыт — приходи завтра.", YELLOW)
            return
        self.game.gym.gym_screen(self.game.player)

    def do_rest(self) -> None:
        player = self.game.player
        if not self.has_slots():
            self.ui.print_line("День уже расписан — только спать.", YELLOW)
            return
        self.use_slot()
        player.energy = min(ENERGY_PER_DAY, player.energy + 40)
        player.heal(5)
        self.ui.print_line("Ты плюнул на дела и подремал. Полегчало.", GREEN)

    # --- панель статуса ---

    def show_day_status(self) -> None:
        player = self.game.player
        self.ui.clear()
        self.ui.divider()
        self.ui.bar("HP", player.hp, player.max_hp,
                    color=RED if player.hp < 40 else "")
        self.ui.bar("Энергия", player.energy, ENERGY_PER_DAY)
        self.ui.bar("Розыск", player.heat, 100, color=YELLOW if player.heat else "")
        self.ui.print_line(
            f"  Деньги       {player.money:,} ₽   Долг: {player.debt:,} ₽")
        self.ui.print_line(
            f"  Репутация    {player.reputation}/1000   "
            f"Слотов свободно: {self.slots_free}/{SLOTS_PER_DAY}")
        if player.job_id:
            from king_city.systems.labor import JOBS
            self.ui.print_line(f"  Работа       {JOBS[player.job_id]['name']}")


# (ключ, подпись) — секунда колонки насыщения позже системами
DAY_MENU = [
    ("1", "Торговля на рынке района"),
    ("2", "Легальная работа"),
    ("3", "Спортзал / книги / курсы"),
    ("4", "Ограбление"),
    ("5", "Разведка района"),
    ("6", "Бандитские дела"),
    ("7", "Связи и взятки"),
    ("8", "Имущество"),
    ("9", "Отдых"),
    ("0", "Спать — завершить день"),
]
