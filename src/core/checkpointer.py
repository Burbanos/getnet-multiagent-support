from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def build_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    return SqliteSaver(conn)
