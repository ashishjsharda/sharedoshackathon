# trustmesh_sdk.py - Simple Python SDK for TrustMesh
"""
TrustMesh Python SDK
Usage:
    from trustmesh_sdk import TrustMesh

    tm = TrustMesh(api_key="your_key")
    trust = tm.get_trust_score("agent_123")
    print(f"Trust: {trust.overall_score}")
"""

import requests
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class Outcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    DISPUTED = "disputed"


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

    def is_trustworthy(self, threshold: float = 0.7) -> bool:
        """Check if agent meets trust threshold"""
        return self.overall_score >= threshold

    def __str__(self):
        return (
            f"{self.agent_name} (#{self.rank if self.rank else '?'})\n"
            f"  Trust Score: {self.overall_score:.3f}\n"
            f"  Success Rate: {self.success_rate:.1%}\n"
            f"  Interactions: {self.interaction_count}\n"
            f"  Confidence: {self.confidence:.3f}"
        )


class TrustMesh:
    """
    TrustMesh client for integrating agent reputation into your system.

    Example:
        tm = TrustMesh(api_key="tm_abc123")

        # Check trust before interacting
        trust = tm.get_trust_score("agent_xyz")
        if trust.overall_score > 0.7:
            result = interact_with_agent("agent_xyz")
            tm.log_interaction(
                responder_id="agent_xyz",
                outcome=Outcome.SUCCESS if result else Outcome.FAILURE,
                task_type="data_processing"
            )
    """

    def __init__(
            self,
            api_key: str,
            base_url: str = "http://localhost:8000"
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {"X-API-Key": api_key}

    def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to TrustMesh API"""
        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def get_trust_score(self, agent_id: str) -> TrustScore:
        """
        Get trust score for an agent.

        Args:
            agent_id: The agent's unique identifier

        Returns:
            TrustScore object with reputation data

        Example:
            trust = tm.get_trust_score("agent_abc123")
            if trust.is_trustworthy():
                print(f"{trust.agent_name} is trusted!")
        """
        data = self._request("GET", f"/agents/{agent_id}/trust-score")
        return TrustScore(**data)

    def log_interaction(
            self,
            responder_id: str,
            outcome: Outcome,
            task_type: str,
            metadata: Optional[dict] = None
    ) -> str:
        """
        Log an interaction with another agent.

        Args:
            responder_id: The agent you interacted with
            outcome: SUCCESS, FAILURE, or DISPUTED
            task_type: Type of task (e.g., "data_analysis")
            metadata: Optional extra data

        Returns:
            Interaction ID

        Example:
            interaction_id = tm.log_interaction(
                responder_id="agent_xyz",
                outcome=Outcome.SUCCESS,
                task_type="image_generation",
                metadata={"duration_ms": 1200}
            )
        """
        data = self._request(
            "POST",
            "/interactions/log",
            headers=self.headers,
            json={
                "responder_id": responder_id,
                "task_type": task_type,
                "outcome": outcome.value,
                "metadata": metadata
            }
        )
        return data["interaction_id"]

    def get_leaderboard(
            self,
            platform: Optional[str] = None,
            limit: int = 10
    ) -> List[TrustScore]:
        """
        Get top agents by trust score.

        Args:
            platform: Filter by platform (e.g., "anthropic")
            limit: Number of results (max 100)

        Returns:
            List of TrustScore objects, ranked

        Example:
            top_agents = tm.get_leaderboard(platform="anthropic", limit=5)
            for agent in top_agents:
                print(agent)
        """
        params = {"limit": limit}
        if platform:
            params["platform"] = platform

        data = self._request("GET", "/leaderboard", params=params)
        return [TrustScore(**item) for item in data]

    def find_trusted_agent(
            self,
            min_score: float = 0.7,
            min_interactions: int = 5,
            platform: Optional[str] = None
    ) -> Optional[TrustScore]:
        """
        Find a trusted agent meeting your criteria.

        Args:
            min_score: Minimum trust score required
            min_interactions: Minimum interaction history
            platform: Preferred platform

        Returns:
            TrustScore of best matching agent, or None

        Example:
            agent = tm.find_trusted_agent(
                min_score=0.8,
                min_interactions=10,
                platform="anthropic"
            )
            if agent:
                print(f"Found trusted agent: {agent.agent_name}")
        """
        leaderboard = self.get_leaderboard(platform=platform, limit=50)

        for agent in leaderboard:
            if (agent.overall_score >= min_score and
                    agent.interaction_count >= min_interactions):
                return agent

        return None

    def get_stats(self) -> dict:
        """Get platform-wide statistics"""
        return self._request("GET", "/stats")


# ==================== Example Usage ====================
if __name__ == "__main__":
    print("🔐 TrustMesh SDK Demo\n")

    # Initialize (you'd get this from registration)
    tm = TrustMesh(api_key="demo_key")

    # Example: Check trust before hiring an agent
    agent_to_hire = "agent_abc123"

    try:
        trust = tm.get_trust_score(agent_to_hire)
        print(f"Checking trust for {trust.agent_name}...")
        print(trust)
        print()

        if trust.is_trustworthy(threshold=0.7):
            print("✅ Agent is trustworthy! Proceeding with hire...")

            # Simulate interaction
            task_success = True  # Your actual interaction here

            # Log the outcome
            interaction_id = tm.log_interaction(
                responder_id=agent_to_hire,
                outcome=Outcome.SUCCESS if task_success else Outcome.FAILURE,
                task_type="data_processing"
            )
            print(f"✅ Interaction logged: {interaction_id}")
        else:
            print("⚠️  Agent trust score too low. Finding alternative...")

            # Find a better agent
            alternative = tm.find_trusted_agent(min_score=0.8)
            if alternative:
                print(f"Found alternative: {alternative.agent_name}")

    except requests.exceptions.HTTPError as e:
        print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("📊 Platform Statistics")
    print("=" * 50)
    stats = tm.get_stats()
    print(f"Total Agents: {stats['total_agents']}")
    print(f"Total Interactions: {stats['total_interactions']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")

    print("\n" + "=" * 50)
    print("🏆 Top 5 Trusted Agents")
    print("=" * 50)
    top_agents = tm.get_leaderboard(limit=5)
    for agent in top_agents:
        print(f"\n{agent}")