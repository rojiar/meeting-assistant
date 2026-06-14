"""Speaker name → Jira accountId mapping."""

from __future__ import annotations

from backend.config import SQLITE_PATH
from backend.models.schemas import SpeakerJiraMap
from backend.services.database import connect, init_db


class AssigneeMapStore:
    def __init__(self, db_path=SQLITE_PATH) -> None:
        init_db(db_path)
        self.db_path = db_path

    def list_all(self) -> list[SpeakerJiraMap]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT speaker_name, jira_account_id, jira_display_name "
                "FROM speaker_jira_map ORDER BY speaker_name"
            ).fetchall()
        return [
            SpeakerJiraMap(
                speaker_name=r["speaker_name"],
                jira_account_id=r["jira_account_id"],
                jira_display_name=r["jira_display_name"] or "",
            )
            for r in rows
        ]

    def get(self, speaker_name: str) -> SpeakerJiraMap | None:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM speaker_jira_map WHERE speaker_name = ?",
                (speaker_name.strip(),),
            ).fetchone()
        if not row:
            return None
        return SpeakerJiraMap(
            speaker_name=row["speaker_name"],
            jira_account_id=row["jira_account_id"],
            jira_display_name=row["jira_display_name"] or "",
        )

    def resolve_account_id(self, speaker_name: str | None) -> str | None:
        if not speaker_name:
            return None
        entry = self.get(speaker_name.strip())
        return entry.jira_account_id if entry else None

    def upsert(self, entry: SpeakerJiraMap) -> SpeakerJiraMap:
        with connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO speaker_jira_map (speaker_name, jira_account_id, jira_display_name)
                VALUES (?, ?, ?)
                ON CONFLICT(speaker_name) DO UPDATE SET
                    jira_account_id = excluded.jira_account_id,
                    jira_display_name = excluded.jira_display_name
                """,
                (
                    entry.speaker_name.strip(),
                    entry.jira_account_id.strip(),
                    (entry.jira_display_name or "").strip(),
                ),
            )
            conn.commit()
        return entry

    def delete(self, speaker_name: str) -> bool:
        with connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM speaker_jira_map WHERE speaker_name = ?",
                (speaker_name.strip(),),
            )
            conn.commit()
            return cur.rowcount > 0
