"""Сохранения в JSON (core/save_manager.py из Плана.txt): слоты, автосейв, зал славы."""

import datetime
import json
import os
from typing import Any, Optional

from king_city.settings import (AUTOSAVE_FILE, HALL_OF_FAME_FILE, SAVE_DIRNAME,
                                SAVE_SLOTS)


class SaveManager:
    """Запись/чтение JSON-файлов в папке king_city/saves/."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir if base_dir is not None else os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.save_dir = os.path.join(self.base_dir, SAVE_DIRNAME)
        os.makedirs(self.save_dir, exist_ok=True)

    # --- пути ---

    def autosave_path(self) -> str:
        return os.path.join(self.save_dir, AUTOSAVE_FILE)

    def slot_path(self, slot: int) -> str:
        if not 1 <= slot <= SAVE_SLOTS:
            raise ValueError(f"Слот {slot} вне диапазона 1..{SAVE_SLOTS}")
        return os.path.join(self.save_dir, f"slot_{slot}.json")

    def hall_of_fame_path(self) -> str:
        return os.path.join(self.save_dir, HALL_OF_FAME_FILE)

    # --- базовые операции ---

    def write(self, path: str, data: Any) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def read(self, path: str) -> Optional[Any]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    # --- высокоуровневые операции ---

    def has_autosave(self) -> bool:
        return os.path.exists(self.autosave_path())

    def save_autosave(self, state: dict) -> None:
        self.write(self.autosave_path(), state)

    def load_autosave(self) -> Optional[dict]:
        return self.read(self.autosave_path())

    def save_slot(self, slot: int, state: dict) -> None:
        self.write(self.slot_path(slot), state)

    def load_slot(self, slot: int) -> Optional[dict]:
        return self.read(self.slot_path(slot))

    def slot_exists(self, slot: int) -> bool:
        return os.path.exists(self.slot_path(slot))

    # --- зал славы ---

    def add_record(self, record: dict) -> None:
        """Дописать итог забега в hall_of_fame.json."""
        records = self.read(self.hall_of_fame_path())
        if not isinstance(records, list):
            records = []
        entry = dict(record)
        entry["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        records.append(entry)
        self.write(self.hall_of_fame_path(), records)
