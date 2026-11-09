"""Local Ogre chat authentication and session storage."""

import hashlib
import hmac
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path


SESSION = re.compile(r"[0-9a-f]{32}")
KEY = re.compile(r"[0-9a-f]{64}")
MAX_TEXT = 32768


class SessionConflict(Exception):
    """A different request committed to this session first."""


def authorized(authorization: str | None) -> bool:
    expected = os.environ.get("SPOT_LOCAL_CHAT_KEY_SHA256", "")
    scheme, _, key = (authorization or "").partition(" ")
    return bool(
        KEY.fullmatch(expected)
        and scheme.lower() == "bearer"
        and KEY.fullmatch(key)
        and hmac.compare_digest(hashlib.sha256(key.encode()).hexdigest(), expected)
    )


class LocalChatHistory:
    def __init__(self, directory: Path):
        self.directory = directory

    def _connect(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.stat(follow_symlinks=False)
        if self.directory.is_symlink() or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise OSError("local chat storage must be private to the service")
        db = sqlite3.connect(self.directory / "ogre.sqlite3", timeout=5)
        try:
            db.execute(
                """CREATE TABLE IF NOT EXISTS exchanges (
                    session TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    user_text TEXT NOT NULL,
                    assistant_text TEXT NOT NULL,
                    PRIMARY KEY (session, revision)
                )"""
            )
        except BaseException:
            db.close()
            raise
        return db

    def load(self, session: str, limit: int):
        with closing(self._connect()) as db:
            rows = db.execute(
                """SELECT revision, user_text, assistant_text FROM exchanges
                   WHERE session = ? ORDER BY revision DESC LIMIT ?""",
                (session, limit),
            ).fetchall()
        messages = []
        for _, user, assistant in reversed(rows):
            messages.extend((
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ))
        return (rows[0][0] if rows else 0), messages

    def commit(self, session: str, revision: int, user: str, assistant: str):
        if len(user) > MAX_TEXT or len(assistant) > MAX_TEXT:
            raise ValueError("local chat message is too long")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM exchanges WHERE session = ?",
                (session,),
            ).fetchone()[0]
            if revision != current:
                raise SessionConflict
            db.execute(
                "INSERT INTO exchanges VALUES (?, ?, ?, ?)",
                (session, revision + 1, user, assistant),
            )
