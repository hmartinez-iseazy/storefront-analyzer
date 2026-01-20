import aiosqlite
import json
import os
from datetime import datetime
from typing import Optional

DATABASE_PATH = os.getenv("DATABASE_PATH", "./storefront_analyzer.db")


async def init_db():
    """Initialize the database and create tables if they don't exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT NOT NULL,
                image_filename TEXT NOT NULL,
                result_json TEXT NOT NULL,
                tokens_input INTEGER NOT NULL,
                tokens_output INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_store_id ON analyses(store_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON analyses(created_at)
        """)
        await db.commit()


async def save_analysis(
    store_id: str,
    image_filename: str,
    result_json: dict,
    tokens_input: int,
    tokens_output: int
) -> int:
    """Save an analysis result to the database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO analyses (store_id, image_filename, result_json, tokens_input, tokens_output, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                store_id,
                image_filename,
                json.dumps(result_json, ensure_ascii=False),
                tokens_input,
                tokens_output,
                datetime.utcnow().isoformat()
            )
        )
        await db.commit()
        return cursor.lastrowid


async def get_analysis(analysis_id: int) -> Optional[dict]:
    """Get a single analysis by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM analyses WHERE id = ?",
            (analysis_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "store_id": row["store_id"],
                "image_filename": row["image_filename"],
                "result_json": json.loads(row["result_json"]),
                "tokens_input": row["tokens_input"],
                "tokens_output": row["tokens_output"],
                "created_at": row["created_at"]
            }
        return None


async def get_analyses_by_store(store_id: str, limit: int = 50) -> list[dict]:
    """Get all analyses for a specific store."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM analyses
            WHERE store_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (store_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "store_id": row["store_id"],
                "image_filename": row["image_filename"],
                "result_json": json.loads(row["result_json"]),
                "tokens_input": row["tokens_input"],
                "tokens_output": row["tokens_output"],
                "created_at": row["created_at"]
            }
            for row in rows
        ]
