"""SQLite-backed storage for versioned prompt templates.

Every update to a prompt creates a new immutable version row, so the full
history of a template is preserved and any past version can be retrieved.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    template TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE (prompt_id, version)
);
"""

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NotFoundError(KeyError):
    """Raised when a prompt id does not exist."""


class DuplicateNameError(ValueError):
    """Raised when creating a prompt with an existing name."""


class MissingVariableError(ValueError):
    """Raised when rendering a template with unfilled placeholders."""


class PromptStore:
    def __init__(self, db_path: str = "promptlab.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def placeholders(template: str) -> list[str]:
        """Return the unique {variable} placeholders in a template, in order."""
        seen: list[str] = []
        for match in _PLACEHOLDER_RE.finditer(template):
            name = match.group(1)
            if name not in seen:
                seen.append(name)
        return seen

    def _latest_row(self, prompt_id: int) -> sqlite3.Row:
        row = self._conn.execute(
            """
            SELECT p.id, p.name, v.version, v.template, v.description, v.created_at
            FROM prompts p
            JOIN prompt_versions v ON v.prompt_id = p.id
            WHERE p.id = ?
            ORDER BY v.version DESC
            LIMIT 1
            """,
            (prompt_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"prompt {prompt_id} not found")
        return row

    # -- CRUD ------------------------------------------------------------
    def create(self, name: str, template: str, description: str = "") -> dict:
        with self._lock:
            try:
                cur = self._conn.execute(
                    "INSERT INTO prompts (name, created_at) VALUES (?, ?)",
                    (name.strip(), _now()),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateNameError(f"prompt name {name!r} already exists") from exc
            prompt_id = cur.lastrowid
            self._conn.execute(
                """INSERT INTO prompt_versions
                   (prompt_id, version, template, description, created_at)
                   VALUES (?, 1, ?, ?, ?)""",
                (prompt_id, template, description, _now()),
            )
            self._conn.commit()
            return dict(self._latest_row(prompt_id))

    def get(self, prompt_id: int) -> dict:
        with self._lock:
            return dict(self._latest_row(prompt_id))

    def list(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT p.id, p.name, v.version, v.template, v.description, v.created_at
                FROM prompts p
                JOIN prompt_versions v ON v.prompt_id = p.id
                WHERE v.version = (
                    SELECT MAX(version) FROM prompt_versions WHERE prompt_id = p.id
                )
                ORDER BY p.id
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def versions(self, prompt_id: int) -> list[dict]:
        with self._lock:
            self._latest_row(prompt_id)  # raises NotFoundError if missing
            rows = self._conn.execute(
                """SELECT version, template, description, created_at
                   FROM prompt_versions WHERE prompt_id = ? ORDER BY version""",
                (prompt_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update(self, prompt_id: int, template: str, description: str = "") -> dict:
        with self._lock:
            latest = self._latest_row(prompt_id)
            new_version = latest["version"] + 1
            self._conn.execute(
                """INSERT INTO prompt_versions
                   (prompt_id, version, template, description, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (prompt_id, new_version, template, description, _now()),
            )
            self._conn.commit()
            return dict(self._latest_row(prompt_id))

    def delete(self, prompt_id: int) -> None:
        with self._lock:
            self._latest_row(prompt_id)  # raises NotFoundError if missing
            self._conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            self._conn.commit()

    def render(self, prompt_id: int, variables: dict[str, str]) -> dict:
        prompt = self.get(prompt_id)
        template = prompt["template"]
        missing = [p for p in self.placeholders(template) if p not in variables]
        if missing:
            raise MissingVariableError(
                f"missing variables for template: {', '.join(missing)}"
            )
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace("{" + key + "}", value)
        return {
            "id": prompt["id"],
            "name": prompt["name"],
            "version": prompt["version"],
            "rendered": rendered,
        }
