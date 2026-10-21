"""Ограбления (systems/heist.py из Плана.txt).

Фазы: разведка (интеллект) → выбор цели → исполнение (дым-шанс
провала → драка с охраной на сигнализации) → итог: добыча, heat,
возможный ордер-police (флаг warrant_active включает суд в M5).

Исполнение и разведка = отдельные слоты (разведка повышает шанс и
показывает точную охрану/награду).
"""

from king_city.core.console_ui import CYAN, GREEN, RED, YELLOW, ConsoleUI
from king_city.core.rng import Rng
from king_city.data.heist_targets_data import (HEIST_TARGET_ORDER,
                                               HEIST_TARGETS)
from king_city.models.player import Player
from king_city.systems.combat import FightResult, Fighter, fighter_from_player


class Heist:
    """Экран криминальных гостей: цели, разведка, исполнение."""

    def __init__(self, game, police) -> None:
        self.game = game
        self.ui: ConsoleUI = game.ui
        self.rng: Rng = game.rng
        self.police = police         # systems/police_system.Police
        self.scouted: set = set()    # разведано в этой сессии
    # --- экраны ---

    def heist_screen(self, player: Player) -> None:
        self.ui.header("ОГРАБЛЕНИЯ")
        while True:
            options = [
                (str(index + 1), self._option_name(target_id, player))
                for index, target_id in enumerate(self.available_targets(player))]
            options.append(("0", "Назад"))
            if not self.available_targets(player):
                self.ui.print_line("Пока никто не пустит тебя дальше двора.",
                                   YELLOW)
                key = self.ui.menu("Цели", options)
                if key == "0":
                    return
                continue
            key = self.ui.menu("Цели", options)
            if key == "0":
                return
            target_id = self.available_targets(player)[int(key) - 1]
            self.target_menu(player, target_id)

    def available_targets(self, player: Player) -> list:
        return [tid for tid in HEIST_TARGET_ORDER
                if player.reputation >= HEIST_TARGETS[tid]["req_reputation"]]

    def _option_name(self, target_id: str, player: Player) -> str:
        t = HEIST_TARGETS[target_id]
        scouted = " ✓" if target_id in self.scouted else ""
        return f"{t['name']} (добыча {t['reward_min']}-{t['reward_max']} ₽){scouted}"

    def target_menu(self, player: Player, target_id: str) -> None:
        t = HEIST_TARGETS[target_id]
        while True:
            known = target_id in self.scouted
            guard = f"охрана: {t['guard']} чел" if known else "охрана: неизвестно"
            warrant = (f"риск ордера: {int(t['warrant_chance'] * 100)}%"
                       if known else "риск ордера: н/д")
            self.ui.print_line()
            self.ui.print_line(f"  {t['name']}: {t['description']}", CYAN)
            self.ui.print_line(f"  {guard}   heat: +{t['heat']}   {warrant}")
            key = self.ui.menu(f"Что с {t['name']}?", [
                ("1", "Разведать (1 слот, показывает точные цифры)"),
                ("2", "Погнали! (1 слот)"),
                ("0", "Назад"),
            ])
            if key == "0":
                return
            if key == "1":
                self.scout(player, target_id)
                continue
            if key == "2":
                self.execute(player, target_id)
                return   # после дела — обратно в план дня

    # --- разведка ---

    def scout(self, player: Player, target_id: str) -> None:
        """Слот тратится всегда; интеллект определяет качество инфы."""
        if not self.game.actions.has_slots():
            self.ui.print_line("На разведку нет слота.", YELLOW)
            return
        self.game.actions.use_slot()
        t = HEIST_TARGETS[target_id]
        intel = player.stats.intelligence
        success = intel >= 12 or self.rng.chance(0.3 + intel / 40)
        if success:
            self.scouted.add(target_id)
            self.ui.print_line(
                f"  Разведка: охрана {t['guard']} чел, награда "
                f"{t['reward_min']}-{t['reward_max']} ₽, шанс ордера "
                f"{int(t['warrant_chance'] * 100)}%.", GREEN)
        else:
            self.ui.print_line(
                "  Разведка провалилась: сторож проводил глазами. Без результатов.",
                RED)

    # --- исполнение ---

    def execute(self, player: Player, target_id: str) -> str:
        if not self.game.actions.has_slots():
            self.ui.print_line("На дело нет слота.", YELLOW)
            return "alive"
        self.game.actions.use_slot()
        t = HEIST_TARGETS[target_id]
        outcome = self.run_heist(player, t)
        if outcome == "arrested":
            # задержание → суд через полицию
            self.game.current_sentence = self.police._sentence_for(
                player, self.game.warrant_active)
            self.police._trial(player, self.game)
            return "alive" if player.is_alive() else "dead"
        return "alive" if player.is_alive() else "dead"

    def run_heist(self, player: Player, target: dict) -> str:
        """Игровое дело: шанс успеха, драка при сигнале, делёж. 'ok'/'arrested'."""
        known = target["id"] in self.scouted
        guard = target["guard"]
        chance = (0.75 - guard * 0.055
                  + player.stats.intelligence * 0.008
                  + player.stats.agility * 0.010)
        if not known:
            chance -= 0.12
        chance = max(0.10, min(0.95, chance))
        self.ui.print_line()
        self.ui.print_line(f"— ДЕЛО: {target['name']} —", CYAN)
        if self.rng.chance(chance):
            reward = self.rng.roll(target["reward_min"], target["reward_max"])
            # скрытый процент с себя: благотворность успеху — в сейф (M8)
            player.add_money(reward)
            player.add_heat(target["heat"])
            player.add_reputation(5 + guard // 2)
            self.ui.print_line(f"  Успех! Добыча: +{reward} ₽, репутация "
                               f"+{5 + guard // 2}, heat +{target['heat']}.", GREEN)
            self._aftermath_chance(player, target, caught=False)
            return "ok"
        # провал: сигнализация, драка с охраной
        self.ui.print_line("  Загремела сигнализация!", RED)
        self._guard_fight(player, guard)
        if not player.is_alive():
            return "ok"   # смерть проверит вызывающий
        self._aftermath_chance(player, target, caught=True)
        return "ok"

    def _guard_fight(self, player: Player, guard_level: int) -> None:
        from king_city.systems.combat import fighter_npc
        guard = Fighter(
            name=f"Охранник (ур. {guard_level})",
            strength=8 + guard_level * 2,
            agility=8 + guard_level,
            endurance=10,
            hp=30 + guard_level * 6,
            weapon="Дубина",
            weapon_mult=1.1,
            weapon_accuracy=0.1,
        )
        me = fighter_from_player(player, player.equipped_weapon)
        me.armor_prc = player.equipped_armor.get("protection", 0)
        result: FightResult = self.combat_run(me, guard)
        self.print_journal(result)
        player.hp = result.player_hp_after

    def combat_run(self, me: Fighter, guard: Fighter) -> FightResult:
        from king_city.systems.combat import simulate_fight
        return simulate_fight(me, guard, self.rng)

    def print_journal(self, result: FightResult) -> None:
        for line in result.log:
            self.ui.print_line(line)

    # --- пост-обработки ---

    def _aftermath_chance(self, player: Player, target: dict,
                          caught: bool) -> None:
        """Шанс ордера/задержания после дела."""
        warrant_chance = target["warrant_chance"] * (1.5 if caught else 1.0)
        arrested = caught and self.rng.chance(0.35)
        if self.rng.chance(warrant_chance):
            self.game.warrant_active = True
            self.ui.print_line("  Ориентировку на тебя открыли — ордер активен!",
                               RED)
        if arrested:
            self.ui.print_line("  Во дворе ждал экипаж. Руки за спину.", RED)
            player.add_heat(10)
            self.game.current_sentence = self.police._sentence_for(
                player, self.game.warrant_active)
            self.police._trial(player, self.game)
