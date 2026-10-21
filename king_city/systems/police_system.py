"""Полиция и тюрьма: механика упора полиции в Плана.txt.

Heat копится от действий. При высоком heat копы устраивают проверку
по ИД после «грязных» действий дня. Остановки по нож-пунктам Плана:
  • мелкий heat / без ордеров → штраф или откуп
  • крупный heat + ордер → суд → тюрьма (реальные дни)

Взятки: копам на месте (минус heat, риск подставы) и судье (шанс
освобождения; провал = большой heat и клеймо).
"""

from king_city.core.console_ui import ConsoleUI, CYAN, GREEN, RED, YELLOW
from king_city.core.rng import Rng
from king_city.data.names_data import COP_NAMES
from king_city.models.player import Player

# тюремные параметры
DAYS_PER_HEAT_ARREST = 3      # дней срока за каждую пачку heat при суде
MIN_SENTENCE = 3
MAX_SENTENCE = 90
BRIBE_POLICE_FULL = 1000      # откуп на месте за остановку при heat<50
LIFE_HEAT = 100               # heat 100 + 3-е осуждение = пожизненное


class Police:
    """Розыск, остановки, суд, тюрьма, взятки."""

    def __init__(self, ui: ConsoleUI, rng: Rng) -> None:
        self.ui = ui
        self.rng = rng

    # --- проверки после действий дня ---

    def daily_stop_check(self, player: Player, game) -> None:
        """С шансом растущим от heat копы останавливают игрока."""
        if player.heat <= 0:
            return
        chance = 0.05 + player.heat / 250.0   # до ~45% при heat 100
        if not self.rng.chance(chance):
            return
        cop = self.rng.choice(COP_NAMES)
        self.ui.print_line()
        self.ui.slow(f"Тормозило-момент: {cop} тормозит тебя у третьего отделения.",
                     CYAN)
        # вариант: мелкий товар — штраф; серьёзный heat — арест с судом
        if player.heat < 50 and not game.warrant_active:
            self._minor_stop(player)
        else:
            self._detained(player, game)

    def _minor_stop(self, player: Player) -> None:
        """Лёгкое торможение: лекция / штраф / откуп."""
        options = [
            ("1", "Откупиться деньгами (1000 ₽)"),
            ("2", "Терпеть — штраф и тормозилово"),
        ]
        key = self.ui.menu("Тормозилово", options)
        if key == "1":
            if player.spend(BRIBE_POLICE_FULL):
                player.add_heat(-10 if player.heat >= 10 else -player.heat)
                hidden = self.rng.chance(0.10)
                if hidden:
                    player.add_heat(5)
                    self.ui.print_line("  Откупился… но он всё записал. Подстава.",
                                       YELLOW)
                else:
                    self.ui.print_line("  Дела порешаем, гражданин. Разошлись.", GREEN)
            else:
                self.ui.print_line("  Нет денег на откуп! Штраф вдогон.", RED)
                self._dostoy_penalty(player)
        else:
            self._dostoy_penalty(player)

    def _dostoy_penalty(self, player: Player) -> None:
        fine = min(player.money, self.rng.roll(200, 600))
        player.add_money(-fine)
        player.reduce_heat(3)
        self.ui.print_line(f"  Штраф: −{fine} ₽, heat немного отпустило.", YELLOW)

    def _detained(self, player: Player, game) -> None:
        """Задержание: у игрока есть шанс откупиться покрупнее, иначе суд."""
        if player.money >= 5000 and self.ui.menu(
                "Задержание по серьёзному", [
                    ("1", "Занести 5000 ₽ — полиция всё забывает"),
                    ("2", "Идём в участок — всё равно я чист")
                ]) == "1" and player.heat < 80:
            if player.spend(5000):
                player.reduce_heat(20)
                self.ui.print_line("  Глаза у участкового погасли. Проехали.", GREEN)
                return
        self._trial(player, game)

    # --- суд ---

    def _trial(self, player: Player, game) -> None:
        from king_city.models.prison import Prison
        self.ui.print_line()
        self.ui.slow("Участок. Камера. Протокол. Суд назначен на утро.", CYAN)
        sentence = self._sentence_for(player, game.warrant_active)
        player.arrests += 1
        # взятка судье: шанс отпустить, провал — generous heat и клеймо
        verdict = self.ui.menu("Зал суда", [
            ("1", "Нанять адвоката (3000 ₽, −1 день срока)"),
            ("2", "Занести судье (7000 ₽, шанс закрыть дело)"),
            ("3", "Признать и отсиживать"),
        ])
        if verdict == "1" and player.spend(3000):
            sentence = max(1, sentence - 1)
            self.ui.print_line(f"  Адвокат выправил протокол. Срок: {sentence} дн.",
                               YELLOW)
        elif verdict == "2":
            if player.spend(7000) and self.rng.chance(0.45):
                self.ui.print_line("  Дело замяли. Свобода, но теперь ты в списках.",
                                   GREEN)
                player.add_heat(10)
                game.warrant_active = False
                return
            self.ui.print_line(
                "  Судья деньги принял, а дело закрыть не смог (или не хотел!).",
                RED)
        game.warrant_active = False
        if player.heat >= LIFE_HEAT and player.arrests >= 3:
            # пожизненное — game over
            player.hp = 0
            return
        self.ui.print_line(f"  УКАЗ: к сроку строго — {sentence} дней.", RED)
        Prison.serve(player, game)

    def _sentence_for(self, player: Player, warrant: bool) -> int:
        base = player.heat // 12 * DAYS_PER_HEAT_ARREST
        if warrant:
            base += 15
        return max(MIN_SENTENCE, min(MAX_SENTENCE, base))
