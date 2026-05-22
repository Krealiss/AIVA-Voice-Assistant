"""
Macro Manager — система макросів (сценаріїв) для AIVA
Зберігає і виконує іменовані послідовності команд
"""
import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rapidfuzz import process, fuzz

logger = logging.getLogger("macro_manager")


@dataclass
class Macro:
    id: str
    name: str
    triggers: List[str]      # фрази що запускають макрос
    commands: List[str]      # команди що виконуються
    created_at: str
    last_used: Optional[str] = None
    use_count: int = 0

    def to_dict(self):
        return asdict(self)


class MacroManager:
    """Персистентне сховище і пошук макросів"""

    def __init__(self, db_path: str = "data/macros.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS macros (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    triggers_json TEXT NOT NULL,
                    commands_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used TEXT,
                    use_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        logger.info(f"MacroManager ініціалізовано: {self.db_path}")

    def _row_to_macro(self, row: sqlite3.Row) -> Macro:
        return Macro(
            id=row["id"],
            name=row["name"],
            triggers=json.loads(row["triggers_json"]),
            commands=json.loads(row["commands_json"]),
            created_at=row["created_at"],
            last_used=row["last_used"],
            use_count=row["use_count"],
        )

    def create(self, name: str, triggers: List[str], commands: List[str]) -> Macro:
        import uuid
        macro = Macro(
            id=str(uuid.uuid4())[:8],
            name=name,
            triggers=[t.lower().strip() for t in triggers],
            commands=commands,
            created_at=datetime.now().isoformat(),
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO macros (id, name, triggers_json, commands_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (macro.id, macro.name,
                  json.dumps(macro.triggers, ensure_ascii=False),
                  json.dumps(macro.commands, ensure_ascii=False),
                  macro.created_at))
            conn.commit()
        logger.info(f"Макрос створено: '{name}' (id={macro.id})")
        return macro

    def get(self, macro_id: str) -> Optional[Macro]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM macros WHERE id = ?", (macro_id,)).fetchone()
        return self._row_to_macro(row) if row else None

    def list_all(self) -> List[Macro]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM macros ORDER BY use_count DESC").fetchall()
        return [self._row_to_macro(r) for r in rows]

    def delete(self, macro_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM macros WHERE id = ?", (macro_id,))
            conn.commit()
        return cur.rowcount > 0

    def update(self, macro_id: str, name: str = None,
               triggers: List[str] = None, commands: List[str] = None) -> Optional[Macro]:
        macro = self.get(macro_id)
        if not macro:
            return None
        if name is not None:
            macro.name = name
        if triggers is not None:
            macro.triggers = [t.lower().strip() for t in triggers]
        if commands is not None:
            macro.commands = commands
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE macros SET name=?, triggers_json=?, commands_json=?
                WHERE id=?
            """, (macro.name,
                  json.dumps(macro.triggers, ensure_ascii=False),
                  json.dumps(macro.commands, ensure_ascii=False),
                  macro_id))
            conn.commit()
        return macro

    def record_use(self, macro_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE macros SET use_count = use_count + 1, last_used = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), macro_id))
            conn.commit()

    def find_by_trigger(self, text: str, score_cutoff: int = 80) -> Optional[Macro]:
        """
        Шукає макрос за фразою-тригером (fuzzy matching).
        Повертає найкращий збіг або None.
        """
        text_lower = text.lower().strip()
        macros = self.list_all()
        if not macros:
            return None

        best_macro = None
        best_score = 0

        for macro in macros:
            for trigger in macro.triggers:
                # Точний збіг
                if trigger == text_lower:
                    return macro
                # Fuzzy збіг
                score = fuzz.ratio(text_lower, trigger)
                if score > best_score:
                    best_score = score
                    best_macro = macro

        if best_score >= score_cutoff:
            logger.info(f"Макрос знайдено: '{best_macro.name}' (score={best_score})")
            return best_macro

        return None


# Глобальний екземпляр
macro_manager = MacroManager()
