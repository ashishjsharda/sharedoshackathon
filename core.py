"""Scoring + SQLite helpers with no web framework dependency."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


DB_PATH = "trustmesh.db"


@dataclass
class TrustScore:
    agent_id: str
    agent_name: str
    overall_score: float
    interaction_count: int
    success_rate: float
    confidence: float
    last_updated: str
    rank: Optional[int] = None


class BayesianTrustEngine:
    def __init__(self):
        self.prior_alpha = 1.0
        self.prior_beta = 1.0
        self.time_decay_days = 30

    def calculate_recency_weight(self, timestamp_str: str) -> float:
        timestamp = datetime.fromisoformat(timestamp_str)
        days_ago = (datetime.utcnow() - timestamp.replace(tzinfo=None)).days
        decay_rate = 1.0 / self.time_decay_days
        weight = math.exp(-decay_rate * days_ago)
        return max(0.1, weight)

    def calculate_score(self, interactions: List[tuple]) -> dict:
        if not interactions:
            return {"score": 0.5, "success_rate": 0.0, "confidence": 0.0, "count": 0}

        alpha = self.prior_alpha
        beta = self.prior_beta
        success_count = 0
        total_count = 0

        for outcome, timestamp in interactions:
            if outcome == "pending":
                continue
            weight = self.calculate_recency_weight(timestamp)
            total_count += 1
            if outcome == "success":
                alpha += weight
                success_count += 1
            elif outcome == "failure":
                beta += weight
            elif outcome == "disputed":
                beta += weight * 0.5

        return {
            "score": round(alpha / (alpha + beta), 3),
            "success_rate": round(success_count / total_count, 3) if total_count else 0.0,
            "confidence": round(min(1.0, (alpha + beta - 2) / 50), 3),
            "count": total_count,
        }


engine = BayesianTrustEngine()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
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
    c.execute(
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
    conn.commit()
    conn.close()


def verify_api_key(api_key: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT agent_id FROM agents WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    return row[0] if row else None


def get_agent_info(agent_id: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT agent_id, name, platform, description, created_at FROM agents WHERE agent_id = ?",
        (agent_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "agent_id": row[0],
        "name": row[1],
        "platform": row[2],
        "description": row[3],
        "created_at": row[4],
    }


def get_agent_interactions(agent_id: str) -> List[tuple]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT outcome, timestamp FROM interactions WHERE responder_id = ? ORDER BY timestamp DESC",
        (agent_id,),
    ).fetchall()
    conn.close()
    return rows


def get_trust_score(agent_id: str) -> TrustScore:
    info = get_agent_info(agent_id)
    if not info:
        raise KeyError(agent_id)
    data = engine.calculate_score(get_agent_interactions(agent_id))
    return TrustScore(
        agent_id=agent_id,
        agent_name=info["name"],
        overall_score=data["score"],
        interaction_count=data["count"],
        success_rate=data["success_rate"],
        confidence=data["confidence"],
        last_updated=datetime.utcnow().isoformat(),
    )


def record_interaction(
    initiator_id: str,
    responder_id: str,
    task_type: str,
    outcome: str,
    metadata: Optional[dict] = None,
) -> dict:
    if not get_agent_info(initiator_id):
        raise KeyError(f"initiator {initiator_id}")
    if not get_agent_info(responder_id):
        raise KeyError(f"responder {responder_id}")
    interaction_id = f"int_{uuid.uuid4().hex[:12]}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO interactions
        (interaction_id, initiator_id, responder_id, task_type, outcome, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            interaction_id,
            initiator_id,
            responder_id,
            task_type,
            outcome,
            datetime.utcnow().isoformat(),
            json.dumps(metadata) if metadata else None,
        ),
    )
    conn.commit()
    conn.close()
    return {"interaction_id": interaction_id, "message": "Interaction logged successfully"}


init_db()
