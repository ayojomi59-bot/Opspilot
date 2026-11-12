import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone


class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, message TEXT NOT NULL, status TEXT NOT NULL,
              plan TEXT NOT NULL, results TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS approvals (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
              action TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
              decision_note TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, customer_id TEXT,
              status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL, event TEXT NOT NULL,
              details TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """)

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_run(self, message: str, status: str, plan: list[str], results: list[dict[str, Any]]) -> str:
        run_id = str(uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?)",
                       (run_id, message, status, json.dumps(plan), json.dumps(results), self.now()))
        return run_id

    def get_run(self, run_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        return {**dict(row), "plan": json.loads(row["plan"]), "results": json.loads(row["results"])}

    def create_approval(self, run_id: str, action: str, payload: dict[str, Any]) -> str:
        approval_id = str(uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (approval_id, run_id, action, json.dumps(payload), "pending", None, self.now()))
            db.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?)",
                       (str(uuid4()), run_id, "approval_requested", json.dumps({"approval_id": approval_id, "action": action}), self.now()))
        return approval_id

    def decide_approval(self, approval_id: str, approve: bool, note: str | None = None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if not row:
                return None
            if row["status"] != "pending":
                return {"status": "already_decided", "payload": json.loads(row["payload"]), "run_id": row["run_id"]}
            status = "approved" if approve else "rejected"
            db.execute("UPDATE approvals SET status=?, decision_note=? WHERE id=?", (status, note, approval_id))
            db.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?)",
                       (str(uuid4()), row["run_id"], f"approval_{status}", json.dumps({"approval_id": approval_id, "note": note}), self.now()))
            return {"status": status, "payload": json.loads(row["payload"]), "run_id": row["run_id"]}

    def create_task(self, title: str, customer_id: str | None = None) -> dict[str, str]:
        task_id = str(uuid4())
        created_at = self.now()
        with self.connect() as db:
            db.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?)", (task_id, title, customer_id, "open", created_at))
        return {"task_id": task_id, "title": title, "status": "open", "created_at": created_at}
