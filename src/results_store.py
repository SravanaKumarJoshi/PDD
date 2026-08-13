"""MySQL persistence for saved screening projects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from src.data import mysql_connection


@dataclass
class SaveStatus:
    success: bool
    message: str
    conflicting_name: str = ""


def _ensure_table() -> None:
    with mysql_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS saved_projects (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            created_at DATETIME NOT NULL,
            requirements JSON NOT NULL,
            ranked_materials JSON NOT NULL,
            request_id VARCHAR(255) NOT NULL,
            pipeline_metadata JSON NOT NULL
        )""")
        connection.commit()
        cursor.close()


def load_results() -> list[dict]:
    _ensure_table()
    with mysql_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT name, created_at, requirements, ranked_materials, request_id, pipeline_metadata FROM saved_projects ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
    for row in rows:
        row["timestamp"] = row.pop("created_at").isoformat()
        for key in ("requirements", "ranked_materials", "pipeline_metadata"):
            if isinstance(row[key], str):
                row[key] = json.loads(row[key])
    return rows


def save_result(name: str, ranked_materials: list[dict], requirements: dict, request_id: str = "", pipeline_metadata: dict | None = None) -> SaveStatus:
    if not name or not name.strip():
        return SaveStatus(False, "Please enter a name for the screening result.")
    _ensure_table()
    try:
        with mysql_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO saved_projects (name, created_at, requirements, ranked_materials, request_id, pipeline_metadata) VALUES (%s, %s, %s, %s, %s, %s)",
                (name.strip(), datetime.now(), json.dumps(requirements), json.dumps(ranked_materials), request_id, json.dumps(pipeline_metadata or {})),
            )
            connection.commit()
            cursor.close()
        return SaveStatus(True, f'Screening result "{name.strip()}" saved in MySQL.')
    except Exception as exc:
        if "Duplicate" in str(exc) or "duplicate" in str(exc):
            return SaveStatus(False, f'A screening result named "{name.strip()}" already exists.', name.strip())
        return SaveStatus(False, f"Unable to save project in MySQL: {exc}")


def rename_result(old_name: str, new_name: str) -> SaveStatus:
    if not new_name or not new_name.strip():
        return SaveStatus(False, "Please enter a new name.")
    _ensure_table()
    try:
        with mysql_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("UPDATE saved_projects SET name = %s WHERE name = %s", (new_name.strip(), old_name))
            connection.commit()
            found = cursor.rowcount
            cursor.close()
        return SaveStatus(bool(found), f'Result renamed to "{new_name.strip()}".' if found else f'Result "{old_name}" not found.')
    except Exception as exc:
        return SaveStatus(False, f"Unable to rename project in MySQL: {exc}")


def delete_result(name: str) -> SaveStatus:
    _ensure_table()
    with mysql_connection() as connection:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM saved_projects WHERE name = %s", (name,))
        connection.commit()
        found = cursor.rowcount
        cursor.close()
    return SaveStatus(bool(found), f'Result "{name}" deleted.' if found else f'Result "{name}" not found.')


def get_result_by_name(name: str) -> dict | None:
    return next((entry for entry in load_results() if entry["name"] == name), None)
