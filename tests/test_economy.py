"""Integration tests for AgentEconomy using mocked Mainlayer HTTP responses."""

from __future__ import annotations

import json
from collections import deque
from typing import Deque

import httpx
import pytest

from src.economy import AgentEconomy, EconomyConfig, EconomyStats
from src.agents.publisher import PublishedPackage


FAKE_API_KEY = "test_integration_key"

# Standard response stubs
_RESOURCE_COUNTER = {"n": 1}

def _resource_response(slug: str = "resource") -> dict:
    rid = f"res_{_RESOURCE_COUNTER['n']:03d}"
    _RESOURCE_COUNTER["n"] += 1
    return {"id": rid, "slug": slug, "price": 0.10, "status": "active"}


def _payment_response(step: str = "payment") -> dict:
    return {
        "payment_id": f"pay_{step}",
        "status": "confirmed",
        "access_token": f"tok_{step}",
    }


def _build_mock_transport(responses: Deque[httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that pops from a deque of pre-built responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        if responses:
            return responses.popleft()
        # Fallback: always return a valid payment
        return httpx.Response(201, json=_payment_response("fallback"))

    return httpx.MockTransport(handler)


def _build_economy_with_mock(response_sequence: list[httpx.Response]) -> AgentEconomy:
    """
    Build an AgentEconomy whose agents all share a single mock transport
    serving responses from the given sequence.
    """
    config = EconomyConfig(api_key=FAKE_API_KEY)
    economy = AgentEconomy(config)

    transport = _build_mock_transport(deque(response_sequence))

    for agent in (
        economy.researcher,
        economy.writer,
        economy.editor,
        economy.translator,
        economy.publisher,
    ):
        agent.client = httpx.AsyncClient(
            base_url="https://api.mainlayer.fr",
            headers={"Authorization": f"Bearer {FAKE_API_KEY}"},
            transport=transport,
        )

    return economy


def _full_pipeline_responses(include_translation: bool = True) -> list[httpx.Response]:
    """
    Build the ordered list of HTTP responses that a full pipeline run expects.

    Order matches the sequence of API calls in publisher.run_pipeline():
    1. 5x POST /resources (register all agents) — during economy.start()
    2. POST /payments (publisher pays researcher)
    3. POST /payments (writer pays researcher)
    4. POST /payments (publisher pays writer)
    5. POST /payments (editor pays writer)
    6. POST /payments (publisher pays editor)
    [if translation]
    7. POST /payments (translator pays writer)
    8. POST /payments (publisher pays translator)
    """
    reg = [httpx.Response(201, json=_resource_response()) for _ in range(5)]
    payments = [
        httpx.Response(201, json=_payment_response("pub_pays_researcher")),
        httpx.Response(201, json=_payment_response("writer_pays_researcher")),
        httpx.Response(201, json=_payment_response("pub_pays_writer")),
        httpx.Response(201, json=_payment_response("editor_pays_writer")),
        httpx.Response(201, json=_payment_response("pub_pays_editor")),
    ]
    if include_translation:
        payments += [
            httpx.Response(201, json=_payment_response("translator_pays_writer")),
            httpx.Response(201, json=_payment_response("pub_pays_translator")),
        ]
    return reg + payments


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAgentEconomyStart:
    async def test_start_registers_all_agents(self):
        responses = [httpx.Response(201, json=_resource_response()) for _ in range(5)]
        economy = _build_economy_with_mock(responses)
        await economy.start()
        assert economy.researcher.resource_id is not None
        assert economy.writer.resource_id is not None
        assert economy.editor.resource_id is not None
        assert economy.translator.resource_id is not None
        assert economy.publisher.resource_id is not None
        await economy.stop()

    async def test_start_sets_running_flag(self):
        responses = [httpx.Response(201, json=_resource_response()) for _ in range(5)]
        economy = _build_economy_with_mock(responses)
        assert economy._running is False
        await economy.start()
        assert economy._running is True
        await economy.stop()

    async def test_stop_clears_running_flag(self):
        responses = [httpx.Response(201, json=_resource_response()) for _ in range(5)]
        economy = _build_economy_with_mock(responses)
        await economy.start()
        await economy.stop()
        assert economy._running is False


@pytest.mark.asyncio
class TestRunTopic:
    async def test_run_topic_returns_published_package(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("AI", include_translation=False)
        assert isinstance(package, PublishedPackage)
        await economy.stop()

    async def test_run_topic_topic_matches(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Robotics", include_translation=False)
        assert package.topic == "Robotics"
        await economy.stop()

    async def test_run_topic_has_research(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Climate", include_translation=False)
        assert "topic" in package.research
        await economy.stop()

    async def test_run_topic_has_content(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Space", include_translation=False)
        assert "title" in package.content
        await economy.stop()

    async def test_run_topic_has_edited_content(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Biotech", include_translation=False)
        assert "body" in package.edited
        await economy.stop()

    async def test_run_topic_with_translation(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=True))
        await economy.start()
        package = await economy.run_topic("Energy", include_translation=True, target_language="Spanish")
        assert "Spanish" in package.translations
        await economy.stop()

    async def test_run_topic_total_spent_positive(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Finance", include_translation=False)
        assert package.total_spent > 0
        await economy.stop()

    async def test_run_topic_has_payment_receipts(self):
        economy = _build_economy_with_mock(_full_pipeline_responses(include_translation=False))
        await economy.start()
        package = await economy.run_topic("Medicine", include_translation=False)
        assert len(package.payment_receipts) >= 5
        await economy.stop()

    async def test_run_topic_raises_if_not_started(self):
        economy = _build_economy_with_mock([])
        with pytest.raises(RuntimeError, match="not started"):
            await economy.run_topic("Test")


@pytest.mark.asyncio
class TestRunSimulation:
    async def test_run_simulation_processes_all_topics(self):
        # 5 registrations + 5 payments per topic * 2 topics (no translation)
        responses = (
            [httpx.Response(201, json=_resource_response()) for _ in range(5)]
            + _full_pipeline_responses(include_translation=False)[5:]
            + _full_pipeline_responses(include_translation=False)[5:]
        )
        economy = _build_economy_with_mock(responses)
        await economy.start()
        stats = await economy.run_simulation(["Topic A", "Topic B"], include_translation=False)
        assert stats.topics_processed == 2
        await economy.stop()

    async def test_run_simulation_returns_economy_stats(self):
        responses = (
            [httpx.Response(201, json=_resource_response()) for _ in range(5)]
            + _full_pipeline_responses(include_translation=False)[5:]
        )
        economy = _build_economy_with_mock(responses)
        await economy.start()
        stats = await economy.run_simulation(["Single Topic"], include_translation=False)
        assert isinstance(stats, EconomyStats)
        await economy.stop()

    async def test_run_simulation_raises_if_not_started(self):
        economy = _build_economy_with_mock([])
        with pytest.raises(RuntimeError, match="not started"):
            await economy.run_simulation(["Topic"])


@pytest.mark.asyncio
class TestContextManager:
    async def test_context_manager_starts_and_stops(self):
        responses = [httpx.Response(201, json=_resource_response()) for _ in range(5)]
        economy = _build_economy_with_mock(responses)
        async with economy:
            assert economy._running is True
        assert economy._running is False


@pytest.mark.asyncio
class TestEconomyStats:
    async def test_stats_summary_format(self):
        stats = EconomyStats()
        assert "Topics processed" in stats.summary()

    async def test_stats_add_package_increments_topics(self):
        # Build a minimal fake package
        responses = _full_pipeline_responses(include_translation=False)
        economy = _build_economy_with_mock(responses)
        await economy.start()
        package = await economy.run_topic("Test", include_translation=False)
        stats = EconomyStats()
        stats.add_package(package)
        assert stats.topics_processed == 1
        await economy.stop()
