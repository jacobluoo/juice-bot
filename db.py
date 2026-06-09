import aiosqlite
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "economy.db"


class Database:
    def __init__(self):
        self._db: aiosqlite.Connection | None = None

    async def setup(self) -> None:
        self._db = await aiosqlite.connect(DB_PATH)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS balances (
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                balance     INTEGER NOT NULL DEFAULT 100,
                last_daily  TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                user_id     INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                job_name    TEXT,
                job_level   INTEGER NOT NULL DEFAULT 1,
                job_xp      INTEGER NOT NULL DEFAULT 0,
                last_work   TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_balances_guild_balance ON balances (guild_id, balance DESC)"
        )
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                name        TEXT NOT NULL,
                created_by  TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                UNIQUE(guild_id, name)
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS updates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL REFERENCES projects(id),
                user        TEXT NOT NULL,
                message     TEXT NOT NULL,
                timestamp   TEXT NOT NULL
            )
        """)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def _ensure_balance_row(self, user_id: int, guild_id: int) -> None:
        async with self._db.execute(
            "SELECT 1 FROM balances WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cursor:
            exists = await cursor.fetchone()
        if not exists:
            await self._db.execute(
                "INSERT OR IGNORE INTO balances (user_id, guild_id) VALUES (?, ?)",
                (user_id, guild_id),
            )
            await self._db.commit()

    async def get_balance(self, user_id: int, guild_id: int) -> int:
        await self._ensure_balance_row(user_id, guild_id)
        async with self._db.execute(
            "SELECT balance FROM balances WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row["balance"]

    async def add_balance(self, user_id: int, guild_id: int, delta: int) -> int:
        await self._ensure_balance_row(user_id, guild_id)
        async with self._db.execute(
            "UPDATE balances SET balance = MAX(0, balance + ?) WHERE user_id = ? AND guild_id = ? RETURNING balance",
            (delta, user_id, guild_id),
        ) as cursor:
            await self._db.commit()
            row = await cursor.fetchone()
        return row["balance"]

    async def set_balance(self, user_id: int, guild_id: int, amount: int) -> int:
        clamped = max(0, amount)
        await self._db.execute(
            "UPDATE balances SET balance = ? WHERE user_id = ? AND guild_id = ?",
            (clamped, user_id, guild_id),
        )
        await self._db.commit()
        return clamped

    async def get_last_daily(self, user_id: int, guild_id: int) -> str | None:
        await self._ensure_balance_row(user_id, guild_id)
        async with self._db.execute(
            "SELECT last_daily FROM balances WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cursor:
            row = await cursor.fetchone()
        return row["last_daily"]

    async def set_last_daily(self, user_id: int, guild_id: int, date_str: str) -> None:
        await self._db.execute(
            "UPDATE balances SET last_daily = ? WHERE user_id = ? AND guild_id = ?",
            (date_str, user_id, guild_id),
        )
        await self._db.commit()

    async def get_job(self, user_id: int, guild_id: int):
        await self._db.execute(
            "INSERT OR IGNORE INTO jobs (user_id, guild_id) VALUES (?, ?)",
            (user_id, guild_id),
        )
        await self._db.commit()
        async with self._db.execute(
            "SELECT * FROM jobs WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cursor:
            return await cursor.fetchone()

    async def set_job(self, user_id: int, guild_id: int, job_name: str | None) -> None:
        await self.get_job(user_id, guild_id)  # ensure row exists
        await self._db.execute(
            "UPDATE jobs SET job_name = ?, job_level = 1, job_xp = 0, last_work = NULL WHERE user_id = ? AND guild_id = ?",
            (job_name, user_id, guild_id),
        )
        await self._db.commit()

    async def update_job_progress(self, user_id: int, guild_id: int, xp_delta: int, last_work: str) -> None:
        await self._db.execute(
            "UPDATE jobs SET job_xp = job_xp + ?, last_work = ? WHERE user_id = ? AND guild_id = ?",
            (xp_delta, last_work, user_id, guild_id),
        )
        await self._db.commit()

    async def set_job_level(self, user_id: int, guild_id: int, level: int, xp: int) -> None:
        await self._db.execute(
            "UPDATE jobs SET job_level = ?, job_xp = ? WHERE user_id = ? AND guild_id = ?",
            (level, xp, user_id, guild_id),
        )
        await self._db.commit()

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list:
        async with self._db.execute(
            """
            SELECT user_id, balance FROM balances
            WHERE guild_id = ?
            ORDER BY balance DESC
            LIMIT ?
            """,
            (guild_id, limit),
        ) as cursor:
            return await cursor.fetchall()

    async def create_project(self, guild_id: int, name: str, created_by: str) -> int | None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with self._db.execute(
            "INSERT OR IGNORE INTO projects (guild_id, name, created_by, created_at) VALUES (?, ?, ?, ?)",
            (guild_id, name, created_by, created_at),
        ) as cursor:
            await self._db.commit()
            if cursor.lastrowid != 0:
                return cursor.lastrowid
        return None

    async def get_project(self, guild_id: int, name: str):
        async with self._db.execute(
            "SELECT * FROM projects WHERE guild_id = ? AND name = ?",
            (guild_id, name),
        ) as cursor:
            return await cursor.fetchone()

    async def list_projects(self, guild_id: int) -> list:
        async with self._db.execute(
            "SELECT * FROM projects WHERE guild_id = ? ORDER BY created_at ASC",
            (guild_id,),
        ) as cursor:
            return await cursor.fetchall()

    async def add_update(self, project_id: int, user: str, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO updates (project_id, user, message, timestamp) VALUES (?, ?, ?, ?)",
            (project_id, user, message, timestamp),
        )
        await self._db.commit()

    async def get_recent_updates(self, project_id: int, limit: int = 5) -> list:
        async with self._db.execute(
            "SELECT * FROM updates WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?",
            (project_id, limit),
        ) as cursor:
            return await cursor.fetchall()
