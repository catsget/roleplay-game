"""Каталог запрещённых товаров (data/drugs_data.py из Плана.txt).

Каталог: базовая цена, доля колебаний, вес единицы, прирост розыска
при обыске. Каждая единица — одна «розничная порция»; торговля идёт
партиями по несколько единиц за сделку.

Правило проекта: НИКАКИХ реальных рецептов/дозировок — это игровые
модели с игровыми ценами.
"""

from king_city.models.item import Item, ItemType

# id, имя, базовая цена ₽, вес кг, min/max доли цены, прирост розыска за единицу
DRUGS_SPEC = [
    ("plan",    "Анаша (план)",  900,   0.4, 0.4, 1.4, 1),
    ("hash",    "Гашиш",         1800,  0.5, 0.4, 1.4, 2),
    ("mda",     "Экстази (MDA)", 1600,  0.1, 0.4, 1.6, 3),
    ("amph",    "Амфетамин",     1200,  0.1, 0.4, 1.7, 3),
    ("lsd",     "ЛСД (марки)",   3500,  0.1, 0.4, 1.8, 4),
    ("meph",    "Мефедрон",      2200,  0.1, 0.4, 1.7, 4),
    ("spice",   "Соль (микс)",   1000,  0.1, 0.3, 2.0, 3),
    ("methad",  "Метадон",       2500,  0.1, 0.5, 1.8, 5),
    ("coke",    "Кокаин",        4200,  0.1, 0.5, 1.9, 6),
    ("heroin",  "Героин",        3200,  0.2, 0.5, 2.0, 6),
]


def build_drugs() -> dict:
    """Собирает каталог товаров по спецификации: {item_id: Item}."""
    catalog = {}
    for (item_id, name, base, weight, pmin, pmax, heat) in DRUGS_SPEC:
        catalog[item_id] = Item(
            item_id=item_id,
            name=name,
            type=ItemType.DRUG,
            base_price=base,
            weight=weight,
            price_min_pct=pmin,
            price_max_pct=pmax,
            heat_gain=heat,
        )
    return catalog


DRUG_ORDER = [spec[0] for spec in DRUGS_SPEC]
