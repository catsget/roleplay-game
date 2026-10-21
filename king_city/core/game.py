"""Главный цикл игры (core/game.py из Плана.txt).

M1: новая игра → цикл дня (действие + сон) → финализация → проверка конца.
Торговля, бой, полиция и прочее добавляются милями M2-M9.
"""

from king_city.core.console_ui import CYAN, GREEN, RED, YELLOW, ConsoleUI
from king_city.core.rng import Rng
from king_city.core.save_manager import SaveManager
from king_city.data.drugs_data import build_drugs
from king_city.models.player import Player
from king_city.models.world import World
from king_city.settings import (DAYS_TOTAL, DEBT_DANGER_LIMIT, DEBT_TERM_DAYS,
                                ENERGY_PER_DAY, HEAT_DECAY, HEAT_DECAY_LEGAL,
                                SAVE_VERSION, START_DEBT, START_MONEY,
                                WIN_DISTRICTS, WIN_MONEY, WIN_REPUTATION)
from king_city.systems.economy import Economy
from king_city.systems.gym import Gym
from king_city.systems.heist import Heist
from king_city.systems.labor import Labor
from king_city.systems.police_system import Police
from king_city.systems.trading import Trading
from king_city.systems.actions import Actions

# Знак валюты в интерфейсах
MONEY_SIGN = "₽"


class Game:
    """Связывает UI, модели и системы. Знает про текущий забег."""

    def __init__(self, ui: ConsoleUI) -> None:
        self.ui = ui
        # seed воспроизводимости тестов: KING_CITY_SEED=42 python main.py
        import os
        seed_env = os.environ.get("KING_CITY_SEED")
        self.rng = Rng(int(seed_env) if seed_env else None)
        self.saves = SaveManager()
        self.economy = Economy(self.rng)
        self.trading = Trading(self.ui, self.rng, self.economy)
        self.labor = Labor(self.ui, self.rng, None)   # actions подключается ниже
        self.gym = Gym(self.ui, self.rng, None)       # actions подключается ниже
        self.police = Police(self.ui, self.rng)
        self.heist = Heist(self, self.police)
        self.warrant_active = False   # есть ордер (появится с M6)
        self.current_sentence = 0
        self.drug_catalog = build_drugs()
        self.player: Player | None = None
        self.world: World | None = None
        self.actions = Actions(self, self.ui)
        self.labor.actions = self.actions
        self.gym.actions = self.actions
        self.slots_used = 0

    # ---------- главный цикл меню ----------

    def run(self) -> None:
        """Главное меню: новая игра / продолжить / выйти."""
        self.ui.header("КОРОЛЬ ГОРОДА — криминальная RPG")
        self.ui.slow("Сталижск. 1998. У тебя в кармане мелочь и большие планы.", CYAN)
        while True:
            try:
                self.main_menu_step()
            except EOFError:
                self.ui.print_line("Ввод закрыт. Пока!", YELLOW)
                return

    def main_menu_step(self) -> None:
            choice = self.ui.menu("Главное меню", [
                ("1", "Новая игра"),
                ("2", "Продолжить (автосохранение)"),
                ("3", "Выход"),
            ])
            if choice == "1":
                try:
                    self.new_game()
                except EOFError:
                    # ввод закрыт (например, Ctrl+Z): сохранены только границы дня
                    self.ui.print_line("Ввод закрыт. Забег прерван. Пока!", YELLOW)
                    self.player = None
                    self.world = None
            elif choice == "2":
                self.continue_game()
            else:
                self.ui.print_line("Удачного прогона по асфальту. Пока!", CYAN)
                return
    # ---------- старт/загрузка забега ----------

    def new_game(self) -> None:
        name = self.ui.ask("Как тебя зовут на районе?")
        self.player = Player(name)
        self.player.money = START_MONEY
        self.player.debt = START_DEBT
        self.player.energy = ENERGY_PER_DAY
        for item in self.drug_catalog.values():
            self.player.inventory.register(item)
        self.world = World()
        self.world.debt_deadline = DEBT_TERM_DAYS
        self.economy.regenerate(self.world.day)
        self.slots_used = 0
        self.intro()
        self.run_session()

    def intro(self) -> None:
        ui = self.ui
        ui.print_line()
        ui.slow("Тебя затянуло по уши: квартплата, долги кредиторам и большие планы.")
        ui.print_line()
        ui.print_line(
            f"Стартовые условия: {self.player.money} {MONEY_SIGN} в кармане, "
            f"долг {self.player.debt} {MONEY_SIGN} нужно закрыть "
            f"до дня {self.world.debt_deadline}."
        )
        ui.print_line(
            "Цель: стать Королём города — "
            f"{WIN_MONEY:,} {MONEY_SIGN} капитала, репутация {WIN_REPUTATION}/1000, "
            f"{WIN_DISTRICTS} района под контролем, за {DAYS_TOTAL} дней."
        )
        ui.print_line()
        ui.pause()

    def continue_game(self) -> None:
        state = self.saves.load_autosave()
        if state is None:
            self.ui.print_line("Автосохранения нет — начни новую игру.", YELLOW)
            return
        if state.get("version") != SAVE_VERSION:
            self.ui.print_line("Сохранение устарело. Начни новую игру.", YELLOW)
            return
        self.player = Player.from_dict(state["player"], catalog=self.drug_catalog)
        self.world = World.from_dict(state["world"])
        self.economy.load_dict(state.get("economy", {}))
        gym_state = state.get("gym", {})
        self.gym.soft_counters = gym_state.get("soft_counters", self.gym.soft_counters)
        self.warrant_active = state.get("warrant_active", False)
        self.slots_used = state.get("slots_used", 0)
        self.ui.print_line(f"Продолжаем забег, {self.player.name}. День "
                           f"{self.world.day}/{DAYS_TOTAL}.", GREEN)
        self.run_session()

    # ---------- дневной цикл ----------

    def run_session(self) -> None:
        """Игра по дням, пока забег не закончится или игрок не выйдет в меню."""
        while True:
            try:
                outcome = self.run_day()
            except EOFError:
                # закрытие ввода — гасим игру аккуратно, сейв на границе дня уже записан
                self.ui.print_line("\nВвод закрыт.", YELLOW)
                outcome = "exit"
            if outcome != "continue":
                break
        # выход из дневного цикла всегда возвращает игрока в главное меню
        self.player = None
        self.world = None

    def run_day(self) -> str:
        """Один игровой день: план → действия → сон. Возвращает 'continue'/'final'."""
        return self.actions.day_loop()

    # ---------- финализация дня ----------

    def finish_day(self) -> str:
        player, world = self.player, self.world
        self.ui.divider()
        self.ui.print_line("Ты завалился на кровать...", CYAN)
        # полиция: спад розыска; на легальной работе быстрее
        decay = HEAT_DECAY
        if player.job_id:
            from king_city.systems.labor import JOBS
            if JOBS[player.job_id]["legal"]:
                decay = HEAT_DECAY_LEGAL
        player.reduce_heat(decay)
        # проценты по долгу
        interest = player.accrue_interest()
        if interest:
            self.ui.print_line(f"Кредиторы накрутили: +{interest} {MONEY_SIGN} долга.",
                               RED)
        if world.day > world.debt_deadline and player.debt > 0:
            self.ui.print_line("Срок возврата долга просрочен!", RED)
        if player.debt > DEBT_DANGER_LIMIT:
            self.ui.print_line(f"Долг перевалил за {DEBT_DANGER_LIMIT} {MONEY_SIGN} "
                               "— коллекторы уже суют нос.", YELLOW)
        # новый день
        player.heal(10)
        player.energy = ENERGY_PER_DAY
        world.next_day()
        # акции рынка на завтра
        self.economy.regenerate(self.world.day)
        # автосохранение
        self.autosave()
        # проверка финалов
        ending = self.check_endings()
        if ending:
            self.show_ending(ending)
            return "final"
        self.ui.print_line(f"Утро дня {world.day}/{DAYS_TOTAL}. Встал, уши заложило.",
                           CYAN)
        return "continue"

    # ---------- проверки финалов ----------

    def capital(self) -> int:
        """Капитал = наличные (позже + имущество + казна банды)."""
        return self.player.money

    def check_endings(self) -> str | None:
        p, w = self.player, self.world
        if not p.is_alive():
            return "dead"
        if (self.capital() >= WIN_MONEY and p.reputation >= WIN_REPUTATION
                and w.controlled_districts >= WIN_DISTRICTS):
            return "king"
        if w.day > DAYS_TOTAL:
            return "time"
        return None

    def show_ending(self, ending: str) -> None:
        p, w = self.player, self.world
        self.ui.print_line()
        self.ui.header("ФИНАЛ")
        self.ui.print_line()
        if ending == "king":
            self.ui.slow("Ты — КОРОЛЬ ГОРОДА. Сталижск теперь твой.", YELLOW, end="\n")
        elif ending == "dead":
            self.ui.slow("Твоё тело нашли в канаве у ТЭЦ. Так заканчивают неудачники.",
                         RED)
        else:
            self.ui.slow(f"Год закончился. Ты всё ещё мелкий подонок, {p.name}.", DIM)
        # запись в зал славы
        self.saves.add_record({
            "name": p.name,
            "ending": ending,
            "day": w.day,
            "capital": self.capital(),
            "reputation": p.reputation,
            "kills": p.kills,
            "arrests": p.arrests,
            "sentence_served": self.current_sentence if ending in ("dead",) else 0,
        })
        self.ui.print_line("Знаешь, что? Это уже история. Запись — в зал славы.", GREEN)
        self.ui.pause()

    # ---------- сериализация ----------

    def state(self) -> dict:
        return {
            "version": SAVE_VERSION,
            "player": self.player.to_dict(),
            "world": self.world.to_dict(),
            "economy": self.economy.to_dict(),
            "gym": {"soft_counters": dict(self.gym.soft_counters)},
            "warrant_active": self.warrant_active,
            "slots_used": self.slots_used,
        }

    def autosave(self) -> None:
        self.saves.save_autosave(self.state())
