"""Тюрьма (models/prison.py из Плана.txt): срок = реальные дни игры.

События камеры: драки, спокойствие, обиски. За 5 дней тихого поведения
срок смягчают на день. Побег: интеллект + ловкость; провал = срок × 1.5
и карцер (−15 HP).
"""

import math

from king_city.core.console_ui import CYAN
from king_city.core.rng import Rng
from king_city.settings import ENERGY_PER_DAY

# события камеры: (текст, эффект)
CAMERA_EVENTS = [
    ("Сосед просил свистнуть о рейде. Свистнул — зачёт по поведению.", "good"),
    ("Мурчала волна: разговоры о твоих делах. Терпел.", "calm"),
    ("Драка за нижнюю койку. Влез — получил по рёбрам.", "fight"),
    ("Дед с кухни притащил чай. Повезло.", "calm"),
    ("Чьи-то сигареты кончились. Устроили разбор.", "fight"),
    ("Обыск камеры: ничего не нашли. Обошлось.", "calm"),
]

GOOD_EVENT_HP = 0
FIGHT_EVENT_HP = 8        # урон от драки в камере
CAREFUL_DAYS_FOR_REDUCTION = 5   # 5 тихих дней = −1 день срока
ESCAPE_BASE_CHANCE = 0.15
ESCAPE_IT_TEST = 0.03     # +3% за интеллект, +2% за ловкость
ESCAPE_AGI_TEST = 0.02


class Prison:
    """Логика отсидки; вызывается один раз, сидит N дней подряд."""

    @staticmethod
    def serve(player, game, rng: Rng) -> None:
        """Сидеть тюрьму: дни текут, события клетки, побег, выход."""
        sentence = int(getattr(game, "current_sentence", 3))
        prison_ui = game.ui
        prison_ui.print_line()
        prison_ui.slow("Тебя увели за каркасы, где пахнет хлоркой и ушами.", CYAN)
        days = 0
        quiet_streak = 0
        escaped = False
        while player.is_alive() and days < sentence:
            # предложение побега каждые 5 дней, начиная с середины срока
            if days >= max(3, sentence // 2) and (days % 5 == 0):
                escape = prison_ui.menu(
                    f"День {days + 1}-й из {sentence} — обходятся часы", [
                        ("1", "Отсиживаться, тихо"),
                        ("2", "Попробовать ПСЕФ-побег"),
                    ])
                if escape == "2":
                    chance = (ESCAPE_BASE_CHANCE
                              + player.stats.intelligence * ESCAPE_IT_TEST
                              + player.stats.agility * ESCAPE_AGI_TEST)
                    if rng.chance(chance):
                        escaped = True
                        prison_ui.slow("Ты перелез, нырнул, растворился в городе.",
                                       "")
                        break
                    sentence = int(math.ceil(sentence * 1.5)) + 3
                    player.hurt(15)
                    prison_ui.print_line(
                        f"ПСЕФ сорвался! Карцер: −15 HP, срок вырос: "
                        f"{sentence} дней.", "")
                    if days >= sentence:
                        break
            # обычный день камеры
            text, effect = rng.choice(CAMERA_EVENTS)
            prison_ui.print_line(f"  [{days + 1} дн.] {text}")
            if effect == "fight":
                player.hurt(FIGHT_EVENT_HP)
                quiet_streak = 0
            else:
                quiet_streak += 1
            # тихи снижают срок
            if quiet_streak > 0 and quiet_streak % CAREFUL_DAYS_FOR_REDUCTION == 0:
                sentence -= 1
                quiet_streak = 0
                prison_ui.print_line("  Хороший комментарий к делу: срок −1 день.",
                                     "")
            days += 1
        if not escaped:
            prison_ui.slow("Тебя выпустили. У ворот — серость, асфальт, затылок в "
                           "тату возврата к жизни.", "")
        # последствия
        player.reduce_heat(30)
        player.energy = ENERGY_PER_DAY
        #.callback: мест проходит реально: мир двигается на N дней
        game.world.day += days
        # слегка лечим после выпуска
        player.heal(10)
