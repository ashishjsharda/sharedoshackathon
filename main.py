
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uvicorn
import sqlite3
import uuid
import math

# Initialize FastAPI
app = FastAPI(
    title="TrustMesh API",
    description="Reputation layer for AI agents",
    version="0.1.0"
)

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Models ====================
class AgentRegistration(BaseModel):
    name: str
    platform: str  # "anthropic", "google", "microsoft", "openai"
    description: Optional[str] = None


class InteractionLog(BaseModel):
    responder_id: str
    task_type: str
    outcome: str  # "success", "failure", "disputed"
    metadata: Optional[dict] = None


class TrustScoreResponse(BaseModel):
    agent_id: str
    agent_name: str
    overall_score: float
    interaction_count: int
    success_rate: float
    confidence: float
    last_updated: str
    rank: Optional[int] = None


# ==================== Database ====================
def init_db():
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()

    # Agents table
    c.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            platform TEXT NOT NULL,
            description TEXT,
            api_key TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Interactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id TEXT PRIMARY KEY,
            initiator_id TEXT NOT NULL,
            responder_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            outcome TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (initiator_id) REFERENCES agents(agent_id),
            FOREIGN KEY (responder_id) REFERENCES agents(agent_id)
        )
    ''')

    conn.commit()
    conn.close()


init_db()


# ==================== Trust Engine ====================
class BayesianTrustEngine:
    """Calculates trust scores using Beta distribution"""

    def __init__(self):
        self.prior_alpha = 1.0  # Prior successes
        self.prior_beta = 1.0  # Prior failures
        self.time_decay_days = 30

    def calculate_recency_weight(self, timestamp_str: str) -> float:
        """Recent interactions weighted higher"""
        timestamp = datetime.fromisoformat(timestamp_str)
        days_ago = (datetime.utcnow() - timestamp).days
        decay_rate = 1.0 / self.time_decay_days
        weight = math.exp(-decay_rate * days_ago)
        return max(0.1, weight)

    def calculate_score(self, interactions: List[tuple]) -> dict:
        """
        Calculate Bayesian trust score
        Returns: {score, success_rate, confidence}
        """
        if not interactions:
            return {
                "score": 0.5,
                "success_rate": 0.0,
                "confidence": 0.0,
                "count": 0
            }

        alpha = self.prior_alpha
        beta = self.prior_beta
        success_count = 0
        total_count = 0

        for interaction in interactions:
            outcome = interaction[0]
            timestamp = interaction[1]

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

        trust_score = alpha / (alpha + beta)
        success_rate = success_count / total_count if total_count > 0 else 0.0
        confidence = min(1.0, (alpha + beta - 2) / 50)

        return {
            "score": round(trust_score, 3),
            "success_rate": round(success_rate, 3),
            "confidence": round(confidence, 3),
            "count": total_count
        }


trust_engine = BayesianTrustEngine()


# ==================== Helper Functions ====================
def verify_api_key(api_key: str) -> Optional[str]:
    """Verify API key and return agent_id"""
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()
    c.execute('SELECT agent_id FROM agents WHERE api_key = ?', (api_key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def get_agent_info(agent_id: str) -> Optional[dict]:
    """Get agent details"""
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()
    c.execute('''
        SELECT agent_id, name, platform, description, created_at 
        FROM agents WHERE agent_id = ?
    ''', (agent_id,))
    result = c.fetchone()
    conn.close()

    if result:
        return {
            "agent_id": result[0],
            "name": result[1],
            "platform": result[2],
            "description": result[3],
            "created_at": result[4]
        }
    return None


def get_agent_interactions(agent_id: str) -> List[tuple]:
    """Get all interactions for an agent (as responder)"""
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()
    c.execute('''
        SELECT outcome, timestamp 
        FROM interactions 
        WHERE responder_id = ?
        ORDER BY timestamp DESC
    ''', (agent_id,))
    results = c.fetchall()
    conn.close()
    return results


# ==================== API Endpoints ====================

@app.get("/")
def root():
    return {
        "name": "TrustMesh API",
        "version": "0.1.0",
        "description": "Reputation layer for AI agents",
        "docs": "/docs",
        "github": "github.com/[your-username]/trustmesh"
    }


@app.post("/agents/register")
def register_agent(agent: AgentRegistration):
    """Register a new agent"""
    agent_id = f"agent_{uuid.uuid4().hex[:12]}"
    api_key = f"tm_{uuid.uuid4().hex}"

    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()

    try:
        c.execute('''
            INSERT INTO agents (agent_id, name, platform, description, api_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            agent_id,
            agent.name,
            agent.platform,
            agent.description,
            api_key,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Agent already exists")
    finally:
        conn.close()

    return {
        "agent_id": agent_id,
        "api_key": api_key,
        "message": "Agent registered successfully",
        "initial_trust_score": 0.5
    }


@app.get("/agents/{agent_id}/trust-score")
def get_trust_score(agent_id: str) -> TrustScoreResponse:
    """Get trust score for an agent"""
    agent_info = get_agent_info(agent_id)

    if not agent_info:
        raise HTTPException(status_code=404, detail="Agent not found")

    interactions = get_agent_interactions(agent_id)
    trust_data = trust_engine.calculate_score(interactions)

    return TrustScoreResponse(
        agent_id=agent_id,
        agent_name=agent_info["name"],
        overall_score=trust_data["score"],
        interaction_count=trust_data["count"],
        success_rate=trust_data["success_rate"],
        confidence=trust_data["confidence"],
        last_updated=datetime.utcnow().isoformat()
    )


@app.post("/interactions/log")
def log_interaction(
        interaction: InteractionLog,
        x_api_key: str = Header(..., alias="X-API-Key")
):
    """Log an interaction between agents"""
    initiator_id = verify_api_key(x_api_key)

    if not initiator_id:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Verify responder exists
    if not get_agent_info(interaction.responder_id):
        raise HTTPException(status_code=404, detail="Responder agent not found")

    interaction_id = f"int_{uuid.uuid4().hex[:12]}"

    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO interactions 
        (interaction_id, initiator_id, responder_id, task_type, outcome, timestamp, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        interaction_id,
        initiator_id,
        interaction.responder_id,
        interaction.task_type,
        interaction.outcome,
        datetime.utcnow().isoformat(),
        str(interaction.metadata) if interaction.metadata else None
    ))

    conn.commit()
    conn.close()

    return {
        "interaction_id": interaction_id,
        "message": "Interaction logged successfully"
    }


@app.get("/leaderboard")
def get_leaderboard(
        platform: Optional[str] = None,
        limit: int = 10
) -> List[TrustScoreResponse]:
    """Get top agents by trust score"""
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()

    if platform:
        c.execute('''
            SELECT agent_id, name FROM agents 
            WHERE platform = ?
        ''', (platform,))
    else:
        c.execute('SELECT agent_id, name FROM agents')

    agents = c.fetchall()
    conn.close()

    scores = []
    for agent_id, name in agents:
        interactions = get_agent_interactions(agent_id)
        trust_data = trust_engine.calculate_score(interactions)

        scores.append(TrustScoreResponse(
            agent_id=agent_id,
            agent_name=name,
            overall_score=trust_data["score"],
            interaction_count=trust_data["count"],
            success_rate=trust_data["success_rate"],
            confidence=trust_data["confidence"],
            last_updated=datetime.utcnow().isoformat()
        ))

    # Sort by score, then confidence
    scores.sort(key=lambda x: (x.overall_score, x.confidence), reverse=True)

    # Add ranks
    for rank, score in enumerate(scores[:limit], 1):
        score.rank = rank

    return scores[:limit]


@app.get("/stats")
def get_stats():
    """Get overall platform statistics"""
    conn = sqlite3.connect('trustmesh.db')
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM agents')
    total_agents = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM interactions')
    total_interactions = c.fetchone()[0]

    c.execute('''
        SELECT COUNT(*) FROM interactions 
        WHERE outcome = "success"
    ''')
    successful_interactions = c.fetchone()[0]

    conn.close()

    return {
        "total_agents": total_agents,
        "total_interactions": total_interactions,
        "success_rate": round(successful_interactions / total_interactions, 3) if total_interactions > 0 else 0,
        "version": "0.1.0"
    }


# ==================== Run Server ====================
if __name__ == "__main__":
    print("🚀 Starting TrustMesh API...")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔍 API: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)