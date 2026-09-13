# 🔐 TrustMesh

> **A reputation layer for AI agents built on A2A protocol**

[![Status](https://img.shields.io/badge/status-alpha-yellow)](https://github.com/ashishjsharda/trustmesh)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)

**The Problem:** Google's A2A protocol enables agents to communicate, but there's no standard way to evaluate trustworthiness. When Agent A hires Agent B, how does A know B won't fail, leak data, or vanish?

**The Solution:** TrustMesh provides a Bayesian reputation system that tracks agent behavior across interactions, enabling trust-aware agent ecosystems.

---

## 🎯 Why This Matters

The Agent2Agent protocol solved communication. TrustMesh solves reputation.

- ✅ **Portable trust scores** - Work across any A2A-compatible platform
- ✅ **Bayesian scoring** - Smart priors handle cold-start for new agents
- ✅ **Time-weighted** - Recent behavior matters more
- ✅ **Open & transparent** - No black-box algorithms
- ✅ **Simple integration** - 3 lines of code


![Screenshot 2025-10-09 225726](https://github.com/user-attachments/assets/6e723ba4-8590-40ff-a04f-a3434cb0b833)

---

## 🚀 Quick Start

### Install & Run

```bash
# Clone the repo
git clone https://github.com/ashishjsharda/trustmesh.git
cd trustmesh

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

Server runs at `http://localhost:8000`  
API docs at `http://localhost:8000/docs`

### Register Your Agent

```python
import requests

# Register your agent
response = requests.post(
    "http://localhost:8000/agents/register",
    json={
        "name": "MyAgent",
        "platform": "anthropic",
        "description": "Data processing agent"
    }
)

agent_data = response.json()
api_key = agent_data["api_key"]  # Save this!
agent_id = agent_data["agent_id"]
```

### Check Another Agent's Trust Score

```python
# Before interacting with another agent
peer_id = "agent_abc123"
response = requests.get(f"http://localhost:8000/agents/{peer_id}/trust-score")
trust = response.json()

if trust["overall_score"] > 0.7:
    print(f"✅ {trust['agent_name']} is trustworthy ({trust['overall_score']})")
    # Proceed with interaction
else:
    print(f"⚠️  {trust['agent_name']} has low trust ({trust['overall_score']})")
```

### Log An Interaction

```python
# After working with another agent
requests.post(
    "http://localhost:8000/interactions/log",
    headers={"X-API-Key": api_key},
    json={
        "responder_id": peer_id,
        "task_type": "data_analysis",
        "outcome": "success"  # or "failure", "disputed"
    }
)
```

---

## 📊 How Trust Scores Work

TrustMesh uses a **Beta-Binomial Bayesian model**:

1. **Prior**: New agents start at 0.5 (neutral)
2. **Updates**: Each interaction adjusts the score
3. **Time decay**: Recent behavior weighted higher
4. **Confidence**: Increases with more interactions

```python
trust_score = α / (α + β)

where:
  α = prior_successes + weighted_successes
  β = prior_failures + weighted_failures
```

**Example trajectory:**
- New agent: `0.5` (neutral, low confidence)
- After 5 successes: `0.83` (high trust, medium confidence)
- After 50 interactions (90% success): `0.89` (high trust, high confidence)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│        Agent Ecosystem              │
│  (Google, Anthropic, Microsoft)     │
└──────────────┬──────────────────────┘
               │
               │ A2A Protocol
               │
┌──────────────▼──────────────────────┐
│         TrustMesh API               │
│  • Trust Score Engine               │
│  • Interaction Logging              │
│  • Reputation Database              │
└──────────────┬──────────────────────┘
               │
               │
┌──────────────▼──────────────────────┐
│      Developer Tools                │
│  • Python SDK                       │
│  • Web Dashboard (coming soon)      │
│  • CLI (coming soon)                │
└─────────────────────────────────────┘
```

---

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/agents/register` | Register a new agent |
| `GET` | `/agents/{id}/trust-score` | Get trust score |
| `POST` | `/interactions/log` | Log an interaction |
| `GET` | `/leaderboard` | Top agents by trust |
| `GET` | `/stats` | Platform statistics |

Full API documentation: http://localhost:8000/docs

---

## 🎯 Roadmap

### ✅ v0.1 (Current - Oct 2025)
- [x] Core trust algorithm
- [x] REST API
- [x] SQLite backend
- [x] Basic documentation
- [x] Python SDK

### 🚧 v0.2 (Coming Soon)
- [ ] PyPI package
- [ ] A2A middleware integration
- [ ] PostgreSQL support
- [ ] Web dashboard

### 🔮 v0.3 (Future)
- [ ] Dispute resolution
- [ ] Multi-dimensional trust (skill-specific)
- [ ] Reputation portability (import/export)
- [ ] Stake-based bonding

---

## 🤝 Contributing

TrustMesh is early-stage and actively seeking contributors!

**We need help with:**
- 🐛 Bug reports and testing
- 📚 Documentation improvements  
- 🔧 SDK development (TypeScript, Rust)
- 🎨 Web dashboard design
- 🧪 Integration examples

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 💡 Use Cases

### 1. **Agent Marketplaces**
Hire trusted agents based on track record:
```python
agents = trustmesh.get_leaderboard(skill="data_analysis", min_score=0.8)
best_agent = agents[0]
```

### 2. **Multi-Agent Systems**
Agents autonomously assess peers:
```python
if trustmesh.get_score(peer_id) > 0.7:
    delegate_task(peer_id)
else:
    handle_task_internally()
```

### 3. **Economic Incentives**
Pay trusted agents more:
```python
trust = trustmesh.get_score(agent_id)
payment = base_rate * (1 + trust.overall_score)
```

---

## 🔒 Security

- **API Keys**: Required for all interactions
- **Rate Limiting**: 100 requests/hour per agent
- **Input Validation**: All data sanitized
- **Audit Trail**: Immutable interaction logs

**Note:** v0.1 uses SQLite. For production, use PostgreSQL with proper auth.

---

## 📖 Documentation

- **API Reference**: Run the server and visit `/docs` for interactive API documentation
- **Examples**: Check the code examples in this README
- **Algorithm**: Trust scoring uses Beta-Binomial Bayesian modeling (see code comments in `main.py`)

**Questions?** Open an [issue](https://github.com/ashishjsharda/trustmesh/issues)!

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built on the shoulders of giants:
- **Google's A2A Protocol** - Agent communication standard
- **Linux Foundation** - Open governance model
- **Bayesian Statistics** - Trust modeling foundation

---

## 🚀 Join the Movement

Agent trust is the missing piece for scalable AI. Let's build it together.

- ⭐ **Star this repo** if you believe in open agent infrastructure
- 💬 **Join discussions** in Issues
- 🤝 **Contribute** code, docs, or ideas
- 🐦 **Share**: "Building trust for AI agents with TrustMesh"

---

**Made with ❤️ by [Ashish Sharda](https://github.com/ashishjsharda)**  
*Building the reputation layer for the agentic web*
