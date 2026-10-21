"""Меню действий дня (systems/actions.py из Плана.txt).

Ведёт план дня: слоты (3), энергия, распределение действий,
переход к «Спать». Выполняет уже реализованные системы (торговля,
работа, спортзал, отдых) и красиво отказывает на нереализованных.
"""

from king_city.core.console_ui import CYAN, GREEN, RED, YELLOW, ConsoleUI
from king_city.models.player import Player
from king_city.settings import ENERGY_PER_DAY, SLOTS_PER_DAY

# Шанс, что после действия дня на улице выскочит наезд
STREET_ROB_CHANCE = 0.20


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
        """План дня до «Спать». Возвращает результат дня для Game."""
        self.game.slots_used = 0
        from king_city.settings import DAYS_TOTAL
        while True:
            self.show_day_status()   # сам очищает экран
            key = self.ui.menu(
                f"День {self.game.world.day}/{DAYS_TOTAL} — план дня", DAY_MENU)
            if key == "0":
                return self.game.finish_day()
            outcome = self.run_action(key)
            if outcome == "dead":
                return "final"          # умер посреди дня — финал
            if key == "1" and self.game.rng.chance(STREET_ROB_CHANCE):
                return self.street_encounter()

    def run_action(self, key: str) -> str:
        """Действие дня; возвращает 'dead', если игрока убили."""
        if key == "1":
            self.do_trading()
        elif key == "2":
            self.do_job()
        elif key == "3":
            self.do_gym()
        elif key == "4":
            self.do_heist()
        elif key == "5":
            self.do_scout()
        elif key == "7":
            self.do_connections()
        elif key == "9":
            self.do_rest()
        else:
            self.ui.print_line("Эта система появится в следующих обновлениях.",
                               YELLOW)
        # полиция может нагрянуть после(action) — если heat ещё даёт повод
        self.game.police.daily_stop_check(self.game.player, self.game)
        if not self.game.player.is_alive():
            return "dead"
        return "alive"

    # --- ограбления (M6) ---

    def do_heist(self) -> None:
        self.game.heist.heist_screen(self.game.player)

    def do_scout(self) -> None:
        """Разведка района: обзор города (тратит слот)."""
        if not self.has_slots():
            self.ui.print_line("На разведку уже нет слота.", YELLOW)
            return
        self.use_slot()
        player = self.game.player
        self.ui.header("РАЗВЕДКА")
        self.ui.print_line(f"  Розыск города: {player.heat}/100", YELLOW)
        if self.game.warrant_active:
            self.ui.print_line("  ВАЖНО: на тебя открыт ордер — суд будет жёстче.",
                               RED)
        self.ui.print_line("  По городу шепчутся — точные цели ограблений")
        self.ui.print_line("  и их охрану вскрывают из меню «Ограбление» (разведка).")

    # --- связи и взятки (M5) ---

    def do_connections(self) -> None:
        player = self.game.player
        self.ui.header("СВЯЗИ И ВЗЯТКИ")
        self.ui.print_line(f"  Розыск: {player.heat}/100   Долг: {player.debt} ₽",
                           YELLOW)
        key = self.ui.menu("Что делаем?", [
            ("1", "Занести собранным 2500 ₽ (−25 розыска, риск подставы)"),
            ("2", "Погасить долг кредиторам"),
            ("3", "Прикупить железа у знакомого"),
            ("4", "Толковать с фракциями (ждём M7)"),
            ("0", "Назад"),
        ])
        if key == "1":
            if player.spend(2500):
                if self.game.rng.chance(0.15):
                    player.add_heat(10)
                    self.ui.print_line("  Кто-то доложил наверх! Розыск подрос.",
                                       RED)
                else:
                    player.reduce_heat(25)
                    self.ui.print_line("  Розыск сместился под стол. Стало спокойнее.",
                                       GREEN)
            else:
                self.ui.print_line("  Не хватает 2500 ₽.", RED)
        elif key == "2":
            if player.debt <= 0:
                self.ui.print_line("  В долговых не ходишь — не с кого брать.", YELLOW)
            else:
                amount = self.ui.ask_number(
                    f"  Сколько закидываем? (есть {player.money} ₽): ",
                    0, min(player.money, player.debt))
                if amount > 0:
                    paid = player.pay_debt(amount)
                    self.ui.print_line(f"  Погасил {paid} ₽ долга. Осталось "
                                       f"{player.debt} ₽.", GREEN)
        elif key == "3":
            self.black_market(player)
        # 4 — ждёт M7 (фракции)

    # --- чёрный рынок железа (M6) ---

    def black_market(self, player: Player) -> None:
        from king_city.data.armors_data import ARMOR_ORDER, ARMORS
        from king_city.data.weapons_data import WEAPON_ORDER, WEAPONS
        self.ui.print_line()
        self.ui.print_line("— ЧЁРНЫЙ РЫНОК У ЗНАКОМОГО —", CYAN)
        self.ui.print_line()
        items = []
        for wid in WEAPON_ORDER:
            if wid == "fists":
                continue
            w = WEAPONS[wid]
            items.append(("w", wid, w["name"], w["price"],
                          f"урон ×{w['dmg_mult']}"))
        for aid in ARMOR_ORDER:
            a = ARMORS[aid]
            items.append(("a", aid, a["name"], a["price"],
                          f"защита {a['protection']}%"))
        for index, (kind, iid, name, price, effect) in enumerate(items, start=1):
            mark = "*" if (kind == "w" and player.equipped_weapon.get("id") == iid) \
                or (kind == "a" and player.equipped_armor.get("id") == iid) else ""
            self.ui.print_line(f"  [{index}] {name:<20}{price:>6} ₽  ({effect}){mark}")
        self.ui.print_line()
        choice = self.ui.ask_number("Что берём? (0 — ничего): ", 0, len(items))
        if choice == 0:
            return
        kind, iid, name, price, effect = items[choice - 1]
        if not player.spend(price):
            self.ui.print_line(f"  Не хватает {price - player.money} ₽.", RED)
            return
        spec = WEAPONS[iid] if kind == "w" else ARMORS[iid]
        if kind == "w":
            player.equipped_weapon = {"id": iid, "name": spec["name"],
                                      "dmg_mult": spec["dmg_mult"],
                                      "accuracy": spec["accuracy"]}
            self.ui.print_line(f"  {name} теперь твоё. Смотри не отрежь себе.",
                               GREEN)
        else:
            player.equipped_armor = {"id": iid, "name": spec["name"],
                                     "protection": spec["protection"]}
            self.ui.print_line(f"  {name} надет. Стало чуть спокойнее.", GREEN)

    # --- уличные наезды (M4) ---

    def street_encounter(self) -> str:
        """Случайный наезд на улицах после действия. 'final' при смерти."""
        from king_city.data.names_data import STREET_NICKNAMES
        from king_city.systems.combat import (fighter_from_player, fighter_npc,
                                              simulate_fight)
        from king_city.core.console_ui import CYAN, RED
        player = self.game.player
        soup_kid = self.game.rng.choice(STREET_NICKNAMES)
        self.ui.print_line()
        self.ui.slow(f"Из переулка выходит {soup_kid}: «Что-то он ты дорого выглядишь…»",
                     CYAN)
        self.ui.print_line()
        me = fighter_from_player(player, player.equipped_weapon)
        me.armor_prc = player.equipped_armor.get("protection", 0)
        enemy = fighter_npc(soup_kid, self.game.world.day, self.game.rng)
        result = simulate_fight(me, enemy, self.game.rng)
        # печать журнала: линия заголовка циан, попадания по тебе красным,
        # твои попадания зелёным, остальное базово
        self.ui.print_line()
        for line in result.log:
            color = ""
            if line.startswith("—"):
                color = CYAN
            elif f"{player.name} вмазал" in line:
                color = GREEN
            elif player.name in line and ("вмазал" in line or "оглуш" in line):
                color = RED
            self.ui.print_line(line, color)
        self.ui.print_line()
        self.ui.pause()
        # последствия
        if result.winner == player.name:
            player.add_reputation(3)
            if enemy.hp <= 0:
                player.kills += 1
                player.add_heat(8)
            else:
                player.add_heat(3)
            player.add_money(result.loot_money)
            self.ui.print_line(f"Разобрался! Репутация +3, подъём +{result.loot_money} ₽.",
                               GREEN)
        else:
            hurt = max(1, self.game.rng.roll(15, 35))
            player.hurt(hurt)
            self.ui.print_line(f"Тебя натащили по асфальту: −{hurt} HP.", RED)
        if not self.game.player.is_alive():
            self.game.show_ending("dead")
            return "final"
        return "alive"

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
        self.ui.print_line()
        self.ui.print_line(
            f"  Деньги       {player.money:,} ₽   Долг: {player.debt:,} ₽")
        self.ui.print_line(
            f"  Репутация    {player.reputation}/1000   "
            f"Слотов свободно: {self.slots_free}/{SLOTS_PER_DAY}")
        if player.job_id:
            from king_city.systems.labor import JOBS
            self.ui.print_line(f"  Работа       {JOBS[player.job_id]['name']}")
        self.ui.print_line()


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
