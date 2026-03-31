# Multi-Agent Economy

A production-ready demo showing a network of AI agents that **pay each other for tasks** using [Mainlayer](https://mainlayer.fr) — payment infrastructure for AI agents.

Each agent registers a service, charges for access, and purchases from upstream agents — creating a self-sustaining content production economy driven entirely by autonomous payments.

---

## Architecture

```
                         ┌─────────────────────────────────────┐
                         │           Publisher Agent            │
                         │      Orchestrates the pipeline       │
                         │         Pays all other agents        │
                         └──────────────┬──────────────────────┘
                                        │ pays
               ┌────────────────────────┼──────────────────────────┐
               │                        │                          │
               v                        v                          v
   ┌───────────────────┐   ┌────────────────────┐   ┌─────────────────────┐
   │  Researcher Agent │   │   Editor Agent      │   │  Translator Agent   │
   │  Sells: $0.10     │   │  Sells: $0.03       │   │  Sells: $0.04       │
   │  Research Reports │   │  Edited Content     │   │  Translations       │
   └─────────┬─────────┘   └─────────┬──────────┘   └──────────┬──────────┘
             │ sells to                │ buys from               │ buys from
             v                        v                          v
   ┌─────────────────────────────────────────────────────────────────────────┐
   │                          Writer Agent                                   │
   │                 Sells written content at $0.05                          │
   │            Buys research from Researcher ($0.10)                        │
   └─────────────────────────────────────────────────────────────────────────┘

Payment flow per pipeline run (with translation):
  Publisher → Researcher  $0.10   (research)
  Writer    → Researcher  $0.10   (writer purchases research internally)
  Publisher → Writer      $0.05   (content)
  Editor    → Writer      $0.05   (editor purchases content internally)
  Publisher → Editor      $0.03   (editing)
  Translator→ Writer      $0.05   (translator purchases content internally)
  Publisher → Translator  $0.04   (translation)
                          ------
  Total per topic:        ~$0.42
```

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

| Agent | Resource slug | Price | Buys from |
|---|---|---|---|
| `ResearcherAgent` | `research-report` | $0.10 | — |
| `WriterAgent` | `written-content` | $0.05 | Researcher |
| `EditorAgent` | `edited-content` | $0.03 | Writer |
| `TranslatorAgent` | `translated-content` | $0.04 | Writer |
| `PublisherAgent` | `published-package` | $0.20 | All of the above |

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

### BaseAgent

All agents extend `BaseAgent`, which wraps the Mainlayer API:

```python
from src.agents.base_agent import BaseAgent

agent = BaseAgent(
    name="MyAgent",
    api_key="your_key",
    agent_wallet="wallet_address",
)

# Register a service
resource = await agent.setup_service(
    slug="my-service",
    price=0.05,
    description="Does something useful",
)

# Pay for another agent's service
receipt = await agent.pay_for_service(resource_id="res_001")

# Check access
has_access = await agent.check_access(resource_id="res_001")
```

### AgentEconomy

```python
from src.economy import AgentEconomy, EconomyConfig

config = EconomyConfig(api_key="your_key")

async with AgentEconomy(config) as economy:
    # Run one topic through the full pipeline
    package = await economy.run_topic("Artificial Intelligence")
    print(package.summary())

    # Run multiple topics
    stats = await economy.run_simulation(
        topics=["AI", "Climate", "Biotech"],
        include_translation=True,
        target_language="Spanish",
    )
    print(stats.summary())
```

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
