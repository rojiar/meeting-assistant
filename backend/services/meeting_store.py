"""Persist meetings and summaries in SQLite."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.config import MEETINGS_DIR, SQLITE_PATH, SYNTHETIC_DIR
from backend.models.schemas import (
    ActionItem,
    MeetingAnalysis,
    MeetingRecord,
    MeetingTask,
    MeetingType,
    UpdateMeetingRequest,
)
from backend.services.database import connect, get_meta, init_db, set_meta


def _fts_query(raw: str) -> str:
    """Sanitize user input for FTS5 MATCH."""
    cleaned = re.sub(r"[^\w\s\u0600-\u06FF]+", " ", raw, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return ""
    return " ".join(f'"{t}"*' for t in tokens[:8])


class MeetingStore:
    def __init__(
        self,
        db_path: Path = SQLITE_PATH,
        *,
        legacy_json_dir: Path | None = MEETINGS_DIR,
    ) -> None:
        self.db_path = db_path
        self.legacy_json_dir = legacy_json_dir
        init_db(self.db_path)
        self._migrate_legacy_json()
        self._rebuild_fts_if_empty()

    def _sync_fts(self, conn, record: MeetingRecord) -> None:
        conn.execute("DELETE FROM meetings_fts WHERE meeting_id = ?", (record.id,))
        conn.execute(
            "INSERT INTO meetings_fts (meeting_id, title, summary) VALUES (?, ?, ?)",
            (record.id, record.title, record.analysis.summary),
        )

    def _rebuild_fts_if_empty(self) -> None:
        with connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM meetings_fts").fetchone()[0]
            if count > 0:
                return
            rows = conn.execute("SELECT id FROM meetings").fetchall()
            for row in rows:
                record = self.get(row["id"])
                if record:
                    self._sync_fts(conn, record)
            conn.commit()

    def save(self, record: MeetingRecord) -> MeetingRecord:
        analysis = record.analysis
        meeting_type = record.meeting_type or "general"
        tags_json = json.dumps(record.tags or [], ensure_ascii=False)
        project_key = (record.project_key or "").strip()
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO meetings (
                    id, title, transcript, summary, title_en,
                    key_points_json, decisions_json, tasks_json,
                    created_at, source, meeting_type, tags_json, project_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    transcript = excluded.transcript,
                    summary = excluded.summary,
                    title_en = excluded.title_en,
                    key_points_json = excluded.key_points_json,
                    decisions_json = excluded.decisions_json,
                    tasks_json = excluded.tasks_json,
                    created_at = excluded.created_at,
                    source = excluded.source,
                    meeting_type = excluded.meeting_type,
                    tags_json = excluded.tags_json,
                    project_key = excluded.project_key
                """,
                (
                    record.id,
                    record.title,
                    record.transcript,
                    analysis.summary,
                    analysis.title_en,
                    json.dumps(analysis.key_points, ensure_ascii=False),
                    json.dumps(analysis.decisions, ensure_ascii=False),
                    json.dumps(
                        [t.model_dump() for t in analysis.tasks],
                        ensure_ascii=False,
                    ),
                    record.created_at,
                    record.source,
                    meeting_type,
                    tags_json,
                    project_key,
                ),
            )
            self._sync_fts(conn, record)
            conn.commit()
        return record

    def get(self, meeting_id: str) -> MeetingRecord | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_all(
        self,
        *,
        meeting_type: MeetingType | None = None,
        project_key: str | None = None,
        tag: str | None = None,
    ) -> list[MeetingRecord]:
        sql = "SELECT * FROM meetings WHERE 1=1"
        params: list[object] = []
        if meeting_type:
            sql += " AND meeting_type = ?"
            params.append(meeting_type)
        if project_key:
            sql += " AND project_key = ?"
            params.append(project_key.strip())
        if tag:
            sql += " AND tags_json LIKE ?"
            params.append(f'%"{tag.strip()}"%')
        sql += " ORDER BY created_at DESC"
        with connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def search(
        self,
        query: str,
        *,
        limit: int = 30,
        meeting_type: MeetingType | None = None,
        project_key: str | None = None,
        tag: str | None = None,
    ) -> list[MeetingRecord]:
        q = query.strip()
        if not q:
            return self.list_all(
                meeting_type=meeting_type, project_key=project_key, tag=tag
            )[:limit]
        fts_q = _fts_query(q)
        if not fts_q:
            return self.list_all(
                meeting_type=meeting_type, project_key=project_key, tag=tag
            )[:limit]

        with connect(self.db_path) as conn:
            try:
                rows = conn.execute(
                    """
                    SELECT m.* FROM meetings m
                    INNER JOIN meetings_fts f ON m.id = f.meeting_id
                    WHERE meetings_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_q, limit * 3),
                ).fetchall()
            except sqlite3.OperationalError:
                pattern = f"%{q}%"
                rows = conn.execute(
                    """
                    SELECT * FROM meetings
                    WHERE title LIKE ? OR summary LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, limit * 3),
                ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        return self._apply_filters(records, meeting_type, project_key, tag)[:limit]

    @staticmethod
    def _apply_filters(
        records: list[MeetingRecord],
        meeting_type: MeetingType | None,
        project_key: str | None,
        tag: str | None,
    ) -> list[MeetingRecord]:
        out = records
        if meeting_type:
            out = [r for r in out if r.meeting_type == meeting_type]
        if project_key:
            pk = project_key.strip()
            out = [r for r in out if r.project_key == pk]
        if tag:
            t = tag.strip()
            out = [r for r in out if t in r.tags]
        return out

    def update(
        self, meeting_id: str, body: UpdateMeetingRequest
    ) -> MeetingRecord | None:
        record = self.get(meeting_id)
        if not record:
            return None
        if body.title is not None:
            record.title = body.title
            record.analysis.title = body.title
        if body.tags is not None:
            record.tags = body.tags
        if body.project_key is not None:
            record.project_key = body.project_key.strip()
        if body.meeting_type is not None:
            record.meeting_type = body.meeting_type
        return self.save(record)

    def delete(self, meeting_id: str) -> bool:
        with connect(self.db_path) as conn:
            conn.execute("DELETE FROM meetings_fts WHERE meeting_id = ?", (meeting_id,))
            cur = conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            conn.commit()
            return cur.rowcount > 0

    def list_action_items(self, *, open_only: bool = False) -> list[ActionItem]:
        items: list[ActionItem] = []
        for record in self.list_all():
            for idx, task in enumerate(record.analysis.tasks):
                if open_only and task.jira_key:
                    continue
                items.append(
                    ActionItem(
                        meeting_id=record.id,
                        meeting_title=record.title,
                        meeting_type=record.meeting_type,
                        project_key=record.project_key,
                        task_index=idx,
                        title=task.title,
                        title_en=task.title_en,
                        assignee=task.assignee,
                        deadline=task.deadline,
                        priority=task.priority,
                        jira_key=task.jira_key,
                    )
                )
        return items

    def update_task_jira_keys(
        self, meeting_id: str, task_index: int, jira_key: str
    ) -> MeetingRecord | None:
        record = self.get(meeting_id)
        if not record or task_index < 0 or task_index >= len(record.analysis.tasks):
            return None
        record.analysis.tasks[task_index].jira_key = jira_key
        return self.save(record)

    def list_synthetic(self) -> list[dict[str, str]]:
        files = []
        for path in sorted(SYNTHETIC_DIR.glob("*.txt")):
            files.append({"id": path.stem, "filename": path.name, "title": path.stem})
        return files

    def load_synthetic(self, file_id: str) -> str:
        path = SYNTHETIC_DIR / f"{file_id}.txt"
        if not path.exists():
            path = SYNTHETIC_DIR / file_id
        if not path.exists():
            raise FileNotFoundError(f"Synthetic meeting not found: {file_id}")
        return path.read_text(encoding="utf-8")

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_json_dir or not self.legacy_json_dir.is_dir():
            return
        json_files = list(self.legacy_json_dir.glob("*.json"))
        if not json_files:
            return

        with connect(self.db_path) as conn:
            if get_meta(conn, "legacy_json_migrated") == "1":
                return
            for path in json_files:
                try:
                    record = MeetingRecord.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                except Exception:
                    continue
                self.save(record)
            set_meta(conn, "legacy_json_migrated", "1")
            conn.commit()

    @staticmethod
    def _row_to_record(row: object) -> MeetingRecord:
        tasks_raw = json.loads(row["tasks_json"])
        tasks = [MeetingTask.model_validate(t) for t in tasks_raw]
        analysis = MeetingAnalysis(
            title=row["title"],
            title_en=row["title_en"] or "",
            summary=row["summary"],
            key_points=json.loads(row["key_points_json"]),
            decisions=json.loads(row["decisions_json"]),
            tasks=tasks,
        )
        meeting_type = (
            row["meeting_type"] if "meeting_type" in row.keys() else "general"
        )
        tags = json.loads(row["tags_json"]) if "tags_json" in row.keys() else []
        project_key = row["project_key"] if "project_key" in row.keys() else ""
        return MeetingRecord(
            id=row["id"],
            title=row["title"],
            transcript=row["transcript"],
            analysis=analysis,
            created_at=row["created_at"],
            source=row["source"],
            meeting_type=meeting_type,
            tags=tags,
            project_key=project_key or "",
        )

    @staticmethod
    def new_id() -> str:
        return uuid4().hex[:12]

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
