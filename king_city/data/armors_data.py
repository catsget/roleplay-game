"""Броня (data/armors_data.py из Плана.txt): защита в процентах от урона."""

# (id, имя, защита %, вес кг, heat/обыск, цена ₽, описание)
ARMORS_SPEC = [
    ("jacket",  "Кожаная куртка",   10, 1.0, 0, 1500,
     "Гоп-стайл плюс щит от случайных ударов."),
    ("vest",    "Бронижилет",       30, 4.0, 5, 12000,
     "Плотный, жаркий, мешает сидеть, но ой как нужен."),
]

ARMOR_ORDER = [spec[0] for spec in ARMORS_SPEC]
ARMORS = {
    spec[0]: {
        "id": spec[0],
        "name": spec[1],
        "protection": spec[2],
        "weight": spec[3],
        "heat_gain": spec[4],
        "price": spec[5],
        "description": spec[6],
    }
    for spec in ARMORS_SPEC
}


def armors_as_dicts() -> dict:
    return ARMORS
