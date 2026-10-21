"""Легальные/тёмные работы (systems/labor.py из Плана.txt).

Смена = 1 слот + 20 энергии. Зарплата = ставка × (1 + 0.25 × уровень)
с премией от харизмы (0..15%). Повышение каждые 7 смен (+уровень,
+2 репутации). Устройство требует минимума по стату. Легальные смены
усиливают спад розыска в финализации дня.
"""

from typing import TYPE_CHECKING

from king_city.core.console_ui import GREEN, RED, YELLOW, ConsoleUI
from king_city.core.rng import Rng
from king_city.data.jobs_data import LEGIT_ORDER, SHADY_ORDER, jobs_as_dicts
from king_city.models.player import Player

if TYPE_CHECKING:
    from king_city.systems.actions import Actions

JOBS = jobs_as_dicts()

SHIFTS_PER_LEVEL = 7        # смен на один уровень должности
LEVEL_BONUS = 0.25          # +25% к ставке за уровень должности
MAX_LEVEL = 4
SHIFT_ENERGY = 20           # энергия на смену
GOOD_TIP_CHANCE = 0.05      # редкая щедрость клиента: премия 30%


class Labor:
    """Устройство, смены, повышения, увольнения."""

    def __init__(self, ui: ConsoleUI, rng: Rng, actions: "Actions") -> None:
        self.ui = ui
        self.rng = rng
        self.actions = actions       # менеджер слотов дня

    # --- экраны ---

    def jobs_screen(self, player: Player) -> None:
        """Меню работы: статус / вакансии / смена / увольнение."""
        self.ui.header("РАБОТА")
        while True:
            self.show_job_status(player)
            options = [("1", "Обзор вакансий")]
            if player.job_id:
                options.append(
                    ("2", f"Отработать смену ({JOBS[player.job_id]['name']})"))
                options.append(("3", "Уволиться"))
            options.append(("0", "Назад"))
            action = self.ui.menu("Работа", options)
            if action == "1":
                self.browse_jobs(player)
            elif action == "2":
                self.work_shift(player)
            elif action == "3":
                self.quit_job(player)
            else:
                return

    def show_job_status(self, player: Player) -> None:
        self.ui.print_line()
        if player.job_id:
            job = JOBS[player.job_id]
            pay = self.shift_pay_base(player)
            self.ui.print_line(
                f"  Место: {job['name']} (ур. {player.job_level}), "
                f"смена ≈ {pay} ₽, смен отработано: {player.job_shifts}", GREEN)
        else:
            self.ui.print_line("  Ты не пашешь. Денег станет меньше.", YELLOW)

    def browse_jobs(self, player: Player) -> None:
        self.ui.print_line()
        for label, order in (("— ЛЕГАЛЬНЫЕ —", LEGIT_ORDER),
                             ("— ТЁМНЫЕ —", SHADY_ORDER)):
            self.ui.print_line()
            self.ui.print_line(f"  {label}")
            for index, job_id in enumerate(order, start=1):
                job = JOBS[job_id]
                mark = "" if self.requirement_met(player, job) else "  (не пройдёшь)"
                sign = "легально" if job["legal"] else "тёмная"
                self.ui.print_line(
                    f"  [{index}] {job['name']:<22}{job['pay']:>5} ₽  {sign}, "
                    f"{job['heat_per_shift']} heat/смена{mark}")
                self.ui.print_line(f"      {job['description']}")
        self.ui.print_line()
        total = len(LEGIT_ORDER) + len(SHADY_ORDER)
        choice = self.ui.ask_number("Куда устраиваемся? (0 — отмена): ", 0, total)
        if choice == 0:
            return
        self.hire(player, (LEGIT_ORDER + SHADY_ORDER)[choice - 1])

    def hire(self, player: Player, job_id: str) -> None:
        job = JOBS[job_id]
        if not self.requirement_met(player, job):
            self.ui.print_line(
                f"  Тебя не берут: нужен {job['req_stat']} ≥ {job['req_value']}.",
                RED)
            return
        player.job_id = job_id
        player.job_shifts = 0
        player.job_level = 0
        self.ui.print_line(f"  Тебя взяли: {job['name']}. С понедельника.", GREEN)

    def requirement_met(self, player: Player, job: dict) -> bool:
        return getattr(player.stats, job["req_stat"]) >= job["req_value"]

    # --- механика смены ---

    def work_shift(self, player: Player) -> None:
        if not self.actions.has_slots():
            self.ui.print_line("День уже расписан — время спать.", YELLOW)
            return
        if player.energy < SHIFT_ENERGY:
            self.ui.print_line("Нет сил на смену. Отдохни или спать ляг.", RED)
            return
        job = JOBS[player.job_id]
        pay = self.shift_pay_base(player)
        bonus_pct = self.rng.roll(0, 15)
        if self.rng.chance(GOOD_TIP_CHANCE):
            bonus_pct = 30
            self.ui.print_line("  Щедрый клиент дал на чай сверху!", GREEN)
        bonus = int(pay * bonus_pct / 100)
        earned = pay + bonus
        player.add_money(earned)
        player.energy -= SHIFT_ENERGY
        self.actions.use_slot()
        player.job_shifts += 1
        if job["legal"]:
            player.days_worked_legally += 1
        if job["heat_per_shift"]:
            player.add_heat(job["heat_per_shift"])
        self.ui.print_line(
            f"  Смена отработана: +{earned} ₽ (ставка {pay} + премия {bonus} ₽).",
            GREEN)
        self.maybe_promotion(player, job)

    def maybe_promotion(self, player: Player, job: dict) -> None:
        if (player.job_shifts % SHIFTS_PER_LEVEL == 0
                and player.job_level < MAX_LEVEL):
            player.job_level += 1
            player.add_reputation(2)
            self.ui.print_line(
                f"  ПОВЫШЕНИЕ! Уровень {player.job_level}, ставка ≈ "
                f"{self.shift_pay_base(player)} ₽.", GREEN)

    def shift_pay_base(self, player: Player) -> int:
        job = JOBS[player.job_id]
        return int(job["pay"] * (1 + LEVEL_BONUS * player.job_level))

    def quit_job(self, player: Player) -> None:
        if player.job_id is None:
            return
        self.ui.print_line(f"  Уволился с места: {JOBS[player.job_id]['name']}.",
                           YELLOW)
        player.job_id = None
        player.job_shifts = 0
        player.job_level = 0
