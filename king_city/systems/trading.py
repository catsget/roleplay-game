"""Торговая система (systems/trading.py из Плана.txt): экраны покупки/продажи.

Одна торговая сессия = 1 временной слот. Внутри сессии игрок делает
сколько угодно сделок; каждая может качнуть торг от харизмы.
"""

from king_city.core.console_ui import GREEN, RED, YELLOW, ConsoleUI
from king_city.core.rng import Rng
from king_city.data.drugs_data import DRUG_ORDER
from king_city.data.districts_data import DISTRICT_ORDER
from king_city.models.player import Player
from king_city.systems.economy import DRUGS, DISTRICTS, Economy


class Trading:
    """Экраны рынка: выбор района → таблица цен → сделки и торг."""

    def __init__(self, ui: ConsoleUI, rng: Rng, economy: Economy) -> None:
        self.ui = ui
        self.rng = rng
        self.economy = economy

    # --- публичная точка входа (сюда приходит «Действие дня») ---

    def open_market(self, player: Player) -> None:
        """Сессия торговли. Вызывается один раз за день, тратит слот."""
        self.ui.header("РЫНОК СТАЛИЖСКА")
        district_id = self.choose_district()
        while True:
            self.ui.print_line()
            self.show_market_table(district_id, player)
            action = self.ui.menu(f"Рынок района «{DISTRICTS[district_id]['name']}»", [
                ("1", "Купить товар"),
                ("2", "Продать товар"),
                ("3", "Сменить район"),
                ("0", "Закрыть рынок"),
            ])
            if action == "1":
                self.buy_screen(player, district_id)
            elif action == "2":
                self.sell_screen(player, district_id)
            elif action == "3":
                district_id = self.choose_district()
            else:
                return

    # --- выбор района ---

    def choose_district(self) -> str:
        options = [
            (str(index + 1), DISTRICTS[did]["name"])
            for index, did in enumerate(DISTRICT_ORDER)
        ]
        choice = self.ui.menu("Куда поедешь?", options)
        return DISTRICT_ORDER[int(choice) - 1]

    # --- таблица цен ---

    def show_market_table(self, district_id: str, player: Player) -> None:
        ui = self.ui
        ui.divider()
        ui.print_line()
        ui.print_line(f"  {'Товар':<16}{'Закупка':>10}{'Сбыт':>10}   В рюкзаке")
        ui.divider()
        for item_id in DRUG_ORDER:
            buy = self.economy.buy_price(district_id, item_id)
            sell = self.economy.sell_price(district_id, item_id)
            name = DRUGS[item_id].name
            held = player.inventory.count(item_id)
            held_text = f"{held} шт" if held else "—"
            ui.print_line(f"  {name:<16}{buy:>9}₽{sell:>9}₽   {held_text}")
        ui.print_line()
        ui.divider()

    # --- сделки ---

    def buy_screen(self, player: Player, district_id: str) -> None:
        self.ui.print_line()
        self.ui.print_line("— ЗАКУПКА —")
        item_id = self.pick_item(player)
        if item_id is None:
            return
        item = DRUGS[item_id]
        price = self.economy.buy_price(district_id, item_id)
        price = self.haggle(price, player)
        affordable = player.money // price
        by_weight = int(player.inventory.free // item.weight)
        max_qty = max(0, min(affordable, by_weight))
        if max_qty == 0:
            self.ui.print_line("Ни денег, ни места в рюкзаке.", RED)
            return
        self.ui.print_line(f"  Цена: {price} ₽/шт   Максимум: {max_qty} шт", YELLOW)
        qty = self.ui.ask_number("  Сколько берёшь? (0 — отмена): ", 0, max_qty)
        if qty == 0:
            return
        try:
            placed = player.inventory.add(item_id, qty)
        except CapacityError:
            self.ui.print_line("Не поднимаешь столько.", RED)
            return
        spent = price * placed
        player.add_money(-spent)
        self.ui.print_line(
            f"  Купил {placed} шт за {spent} ₽. В кармане: {player.money} ₽.", GREEN)
        # крупные партии иногда дают всплеск розыска (шанс зависит от товара)
        splash = int(placed * item.heat_gain / 3)
        if splash > 0 and self.rng.chance(0.03):
            player.add_heat(min(splash, 10))
            self.ui.print_line("  Сосед по двору смотрел не по-детски… "
                               "рынок не любит шума.", YELLOW)

    def sell_screen(self, player: Player, district_id: str) -> None:
        self.ui.print_line()
        self.ui.print_line("— СБЫТ —")
        item_id = self.pick_item(player, owned_only=True)
        if item_id is None:
            return
        held = player.inventory.count(item_id)
        price = self.economy.sell_price(district_id, item_id)
        price = self.haggle(price, player)
        self.ui.print_line(f"  Цена: {price} ₽/шт   В рюкзаке: {held} шт", YELLOW)
        qty = self.ui.ask_number("  Сколько продаёшь? (0 — отмена): ", 0, held)
        if qty == 0:
            return
        taken = player.inventory.remove(item_id, qty)
        earned = price * taken
        player.add_money(earned)
        self.ui.print_line(
            f"  Продал {taken} шт за {earned} ₽. В кармане: {player.money} ₽.", GREEN)
        # рюкзак пуст от запрещёнки — розыск медленно отпускает
        if player.inventory.total_heat_gain() == 0:
            player.reduce_heat(1)

    # --- торг ---

    def haggle(self, price: int, player: Player) -> int:
        """Торг от харизмы: улучшает цену на 1..10% с шансом 30% + 2%/хар.
        Изредка торговец оказывается барыгой-хитрецом и цену завышает.
        """
        chance = min(0.85, 0.30 + player.stats.charisma * 0.02)
        if not self.rng.chance(chance):
            self.ui.print_line("  Торг не сложился — цена как была.", YELLOW)
            return price
        if self.rng.chance(0.10):  # торговец хитрит и обманывает
            factor = 1.0 + self.rng.roll(5, 15) / 100.0
            new_price = round5(int(price * factor))
            self.ui.print_line(
                f"  Барыга хитрит: «последняя партия» — {new_price} ₽.", RED)
            return new_price
        factor = 1.0 - self.rng.roll(1, 10) / 100.0
        new_price = round5(int(price * factor))
        self.ui.print_line(f"  Утряс цену до {new_price} ₽.", GREEN)
        return new_price

    # --- выбор товара ---

    def pick_item(self, player: Player, owned_only: bool = False) -> str | None:
        """Выбор товара из списка; None = отмена (ключ 0)."""
        item_ids = DRUG_ORDER
        if owned_only:
            if player is None:
                raise ValueError("Для продажи нужен игрок")
            have = [iid for iid in DRUG_ORDER
                    if player.inventory.count(iid) > 0]
            if not have:
                self.ui.print_line("Товара нет — продавать нечего.", RED)
                return None
            item_ids = have
        options = [(str(index + 1), DRUGS[iid].name)
                   for index, iid in enumerate(item_ids)]
        options.append(("0", "Отмена"))
        key = self.ui.menu("Что берём?", options)
        if key == "0":
            return None
        return item_ids[int(key) - 1]


def round5(value: int) -> int:
    return max(5, int(value / 5) * 5)
