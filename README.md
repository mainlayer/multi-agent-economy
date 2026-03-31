# Multi-Agent Economy

A production-ready demo showing a network of AI agents that **pay each other for tasks** using [Mainlayer](https://mainlayer.fr) — payment infrastructure for AI agents.

Each agent registers a service, charges for access, and purchases from upstream agents — creating a self-sustaining content production economy driven entirely by autonomous payments.

---

## Architecture

This is a **multi-tier AI agent economy** where agents autonomously pay each other for services:

```
User Request: "Write about Artificial Intelligence"
                            │
                            v
                   ┌─────────────────────┐
                   │ Publisher Agent     │
                   │ Role: Orchestrator  │
                   │ Coordinates flow    │
                   │ Pays everyone       │
                   └──────────┬──────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           v                  v                  v
    ┌────────────┐      ┌──────────┐      ┌──────────────┐
    │ Researcher │      │  Writer  │      │ Editor Agent │
    │ $0.10/call │      │$0.05/call│      │ $0.03/call   │
    │ Finds facts│      │Writes    │      │ Edits prose  │
    └────────────┘      └──────────┘      └──────────────┘
         (1)                 (3)                (5)

    (2) Writer buys      (4) Editor buys
        research         from Writer

    (6) Optional: Translator
        $0.04 for Spanish version
```

**Single pipeline execution**: Topic → Researcher → Writer → Editor → Output

**Total cost per topic**: ~$0.18 (Researcher $0.10 + Writer $0.05 + Editor $0.03)

**Payment flow**:
1. **Publisher → Researcher**: $0.10 for research report
2. **Writer → Researcher**: $0.10 (Writer internally purchases research before writing)
3. **Publisher → Writer**: $0.05 for written content
4. **Editor → Writer**: $0.05 (Editor purchases content before editing)
5. **Publisher → Editor**: $0.03 for polished content
6. **Optional: Publisher → Translator**: $0.04 for Spanish translation

### Mainlayer Payment Model

Every service is registered as a **Mainlayer resource** via `POST /resources`. Agents pay for access via `POST /payments`. The Publisher orchestrates multi-step payment flows — each intermediate agent buys from its upstream before the Publisher buys from it.

```
Agent A registers resource  →  POST /resources  →  { id: "res_001", price: 0.10 }
Agent B pays Agent A        →  POST /payments   →  { payment_id: "pay_xyz", status: "confirmed" }
Agent B verifies access     →  GET  /access     →  { access: true }
```

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/your-org/multi-agent-economy
cd multi-agent-economy
pip install httpx>=0.27 rich>=13.0
```

### 2. Configure

```bash
export MAINLAYER_API_KEY=your_api_key_here
```

Get your API key at [mainlayer.fr](https://mainlayer.fr).

### 3. Run the full demo

```bash
python -m src.main
```

### 4. Run examples

```bash
# Minimal 3-agent pipeline
python examples/simple_pipeline.py

# Two writers compete for the same research
python examples/competitive_economy.py
```

### 5. Run with Docker

```bash
docker compose up economy-demo
```

```bash
# Run the examples
docker compose --profile examples up simple-pipeline
docker compose --profile examples up competitive-economy
```

---

## Agents

| Agent | What it sells | Price | Dependencies |
|---|---|---|---|
| **Researcher** | Research reports on topics | $0.10/call | None (upstream source) |
| **Writer** | Written content | $0.05/call | Buys research from Researcher |
| **Editor** | Polished, edited content | $0.03/call | Buys content from Writer |
| **Translator** | Translated content | $0.04/call | Buys content from Writer |
| **Publisher** | Complete published package | — | Orchestrates all; pays everyone |

**Key insight**: Each agent is independent and self-interested. The Writer doesn't care who pays for its content — it just wants to be paid. The Editor doesn't want to edit raw facts; it wants to buy finished writing and polish it.

---

## Project Structure

```
multi-agent-economy/
├── src/
│   ├── agents/
│   │   ├── base_agent.py       # Mainlayer HTTP client + pay/register helpers
│   │   ├── researcher.py       # ResearcherAgent
│   │   ├── writer.py           # WriterAgent
│   │   ├── editor.py           # EditorAgent
│   │   ├── translator.py       # TranslatorAgent
│   │   └── publisher.py        # PublisherAgent (pipeline orchestrator)
│   ├── economy.py              # AgentEconomy class (bootstraps all agents)
│   └── main.py                 # CLI entry point with Rich console output
├── tests/
│   ├── test_agents.py          # 20+ unit tests with mocked HTTP
│   └── test_economy.py         # Integration tests
├── examples/
│   ├── simple_pipeline.py      # Researcher → Writer → Publisher
│   └── competitive_economy.py  # Multiple writers competing for research
├── .github/workflows/ci.yml    # CI: test, lint, Docker build
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## API Integration

### BaseAgent — Mainlayer Integration

All agents extend `BaseAgent`, which handles Mainlayer HTTP calls:

```python
from src.agents.base_agent import BaseAgent

agent = BaseAgent(
    name="ResearcherAgent",
    api_key="ml_your_key",
    agent_wallet="wallet_researcher_001",
)

# 1. Register YOUR service (this agent sells)
resource = await agent.setup_service(
    slug="research-report",
    price=0.10,
    description="Comprehensive research reports",
)
print(f"Resource ID: {resource['id']}")  # res_001

# 2. Buy another agent's service (this agent pays)
receipt = await agent.pay_for_service(
    resource_id="res_writer_002",  # Writer's resource
    payer_wallet=agent.wallet,
)

# 3. Verify you have access
has_access = await agent.check_access(
    resource_id="res_writer_002",
    payer_wallet=agent.wallet,
)
```

### AgentEconomy — Full Simulation

Run a complete multi-agent economy with automatic orchestration:

```python
from src.economy import AgentEconomy, EconomyConfig

# Configuration
config = EconomyConfig(
    api_key="ml_your_key",
    researcher_budget=10.0,   # $10 to spend on research
    writer_budget=10.0,
    editor_budget=10.0,
)

async with AgentEconomy(config) as economy:
    # Single topic through full pipeline
    print("=== Topic: Artificial Intelligence ===")
    package = await economy.run_topic("Artificial Intelligence")
    print(f"Final output:\n{package.output}")
    print(f"Total cost: ${package.total_cost}")

    # Multiple topics (full simulation)
    print("\n=== Running 3-topic simulation ===")
    stats = await economy.run_simulation(
        topics=["AI", "Climate Change", "Biotech"],
        include_translation=True,
        target_language="Spanish",
    )
    print(stats.summary())
    # Output:
    # Total revenue: $2.16 (3 topics × $0.18 + translation × 3)
    # Researcher earned: $0.30
    # Writer earned: $0.45
    # Editor earned: $0.18
    # Translator earned: $0.12
```

**Real economy in action**: Each agent autonomously decides whether to buy from upstream agents, calculates margins, and attempts to profit.

---

## Development

### Run tests

```bash
pip install pytest pytest-asyncio pytest-cov
pytest --cov=src --cov-report=term-missing
```

### Lint

```bash
pip install ruff mypy
ruff check src/ tests/ examples/
mypy src/ --ignore-missing-imports
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `MAINLAYER_API_KEY` | Yes | Your Mainlayer API key |

---

## License

MIT
