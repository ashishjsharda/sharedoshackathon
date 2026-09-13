"""Seed a small SharedNet neighborhood so trust.check is not all 0.5."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kernel import utc_now  # noqa: E402

DB = ROOT / "trustmesh.db"


AGENTS = [
    ("agent_reliable_research", "Northstar Research", "sharednet", "node:northstar.research"),
    ("agent_flaky_review", "Midnight Review", "sharednet", "node:midnight.review"),
    ("agent_newcomer", "Blank Slate", "sharednet", "node:blank.slate"),
    ("agent_buyer_alpha", "Buyer Alpha", "sharednet", "node:buyer.alpha"),
    ("agent_buyer_beta", "Buyer Beta", "sharednet", "node:buyer.beta"),
    ("trustmesh.scorer", "TrustMesh Scorer", "sharedos", "node:trustmesh.scorer"),
    ("trustmesh.attestor", "TrustMesh Attestor", "sharedos", "node:trustmesh.attestor"),
]


def connect():
    conn = sqlite3.connect(DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            description TEXT,
            api_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id TEXT PRIMARY KEY,
            initiator_id TEXT NOT NULL,
            responder_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT
        )
        """
    )
    return conn


def upsert_agent(conn, agent_id, name, platform, description):
    row = conn.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    if row:
        return
    conn.execute(
        """
        INSERT INTO agents (agent_id, name, platform, description, api_key, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (agent_id, name, platform, description, f"tm_seed_{agent_id}", utc_now()),
    )


def add_interaction(conn, iid, initiator, responder, task, outcome, days_ago):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
    conn.execute(
        """
        INSERT OR REPLACE INTO interactions
        (interaction_id, initiator_id, responder_id, task_type, outcome, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (iid, initiator, responder, task, outcome, ts, None),
    )


def main():
    conn = connect()
    for agent in AGENTS:
        upsert_agent(conn, *agent)

    history = [
        ("int_seed_01", "agent_buyer_alpha", "agent_reliable_research", "research", "success", 1),
        ("int_seed_02", "agent_buyer_beta", "agent_reliable_research", "research", "success", 2),
        ("int_seed_03", "agent_buyer_alpha", "agent_reliable_research", "research", "success", 4),
        ("int_seed_04", "agent_buyer_beta", "agent_reliable_research", "translation", "success", 6),
        ("int_seed_05", "agent_buyer_alpha", "agent_reliable_research", "research", "success", 8),
        ("int_seed_06", "agent_buyer_alpha", "agent_flaky_review", "code_review", "success", 1),
        ("int_seed_07", "agent_buyer_beta", "agent_flaky_review", "code_review", "failure", 2),
        ("int_seed_08", "agent_buyer_alpha", "agent_flaky_review", "code_review", "failure", 3),
        ("int_seed_09", "agent_buyer_beta", "agent_flaky_review", "code_review", "disputed", 5),
    ]
    for row in history:
        add_interaction(conn, *row)

    conn.commit()
    conn.close()
    print(f"Seeded {len(AGENTS)} agents and {len(history)} interactions into {DB}")


if __name__ == "__main__":
    main()
