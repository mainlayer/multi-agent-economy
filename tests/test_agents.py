"""Unit tests for individual agents with mocked HTTP (20+ tests)."""

from __future__ import annotations

import pytest
import httpx
import pytest_asyncio

from src.agents.base_agent import BaseAgent, MainlayerError
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.agents.editor import EditorAgent
from src.agents.translator import TranslatorAgent
from src.agents.publisher import PublisherAgent, PublishedPackage


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

FAKE_API_KEY = "test_key_abc123"
FAKE_WALLET = "wallet_test_001"

RESOURCE_RESPONSE = {
    "id": "res_001",
    "slug": "research-report",
    "price": 0.10,
    "status": "active",
}

PAYMENT_RESPONSE = {
    "payment_id": "pay_abc123",
    "status": "confirmed",
    "access_token": "tok_xyz",
}

ACCESS_GRANTED = {"access": True}
ACCESS_DENIED = {"access": False}


def _transport_for(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Return a MockTransport that serves each response in order."""
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        idx = call_count["n"]
        call_count["n"] += 1
        if idx >= len(responses):
            return responses[-1]
        return responses[idx]

    return httpx.MockTransport(handler)


def _mock_agent(agent_cls, responses: list[httpx.Response], **kwargs):
    """Construct an agent whose HTTP client uses a mock transport."""
    agent = agent_cls(name="TestAgent", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET, **kwargs)
    agent.client = httpx.AsyncClient(
        base_url="https://api.mainlayer.xyz",
        headers={"Authorization": f"Bearer {FAKE_API_KEY}"},
        transport=_transport_for(responses),
    )
    return agent


# ---------------------------------------------------------------------------
# BaseAgent tests
# ---------------------------------------------------------------------------

class TestBaseAgentInit:
    def test_name_is_stored(self):
        agent = BaseAgent(name="Bob", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        assert agent.name == "Bob"

    def test_wallet_is_stored(self):
        agent = BaseAgent(name="Bob", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        assert agent.agent_wallet == FAKE_WALLET

    def test_resource_id_starts_none(self):
        agent = BaseAgent(name="Bob", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        assert agent.resource_id is None

    def test_service_price_starts_none(self):
        agent = BaseAgent(name="Bob", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        assert agent.service_price is None

    def test_repr_contains_name(self):
        agent = BaseAgent(name="Bob", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        assert "Bob" in repr(agent)


@pytest.mark.asyncio
class TestBaseAgentSetupService:
    async def test_setup_service_returns_data(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(201, json=RESOURCE_RESPONSE)],
        )
        result = await agent.setup_service("test-slug", 0.10, "A test resource")
        assert result["id"] == "res_001"

    async def test_setup_service_sets_resource_id(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(201, json=RESOURCE_RESPONSE)],
        )
        await agent.setup_service("test-slug", 0.10, "A test resource")
        assert agent.resource_id == "res_001"

    async def test_setup_service_sets_price(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(201, json=RESOURCE_RESPONSE)],
        )
        await agent.setup_service("test-slug", 0.10, "A test resource")
        assert agent.service_price == 0.10

    async def test_setup_service_raises_on_error(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(422, text="Validation error")],
        )
        with pytest.raises(MainlayerError) as exc_info:
            await agent.setup_service("test-slug", 0.10, "desc")
        assert exc_info.value.status_code == 422

    async def test_setup_service_accepts_200(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(200, json={**RESOURCE_RESPONSE, "id": "res_200"})],
        )
        result = await agent.setup_service("slug", 0.05, "desc")
        assert result["id"] == "res_200"


@pytest.mark.asyncio
class TestBaseAgentPayForService:
    async def test_pay_for_service_returns_receipt(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(201, json=PAYMENT_RESPONSE)],
        )
        receipt = await agent.pay_for_service("res_001")
        assert receipt["payment_id"] == "pay_abc123"

    async def test_pay_for_service_raises_on_error(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(402, text="Insufficient funds")],
        )
        with pytest.raises(MainlayerError) as exc_info:
            await agent.pay_for_service("res_001")
        assert exc_info.value.status_code == 402

    async def test_pay_for_service_status_confirmed(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(200, json=PAYMENT_RESPONSE)],
        )
        receipt = await agent.pay_for_service("res_001")
        assert receipt["status"] == "confirmed"


@pytest.mark.asyncio
class TestBaseAgentCheckAccess:
    async def test_check_access_returns_true(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(200, json=ACCESS_GRANTED)],
        )
        assert await agent.check_access("res_001") is True

    async def test_check_access_returns_false(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(200, json=ACCESS_DENIED)],
        )
        assert await agent.check_access("res_001") is False

    async def test_check_access_non_200_returns_false(self):
        agent = _mock_agent(
            BaseAgent,
            [httpx.Response(404, text="Not found")],
        )
        assert await agent.check_access("res_001") is False


# ---------------------------------------------------------------------------
# ResearcherAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestResearcherAgent:
    async def test_register_calls_setup_service(self):
        agent = _mock_agent(
            ResearcherAgent,
            [httpx.Response(201, json=RESOURCE_RESPONSE)],
        )
        result = await agent.register()
        assert result["id"] == "res_001"
        assert agent.resource_id == "res_001"

    async def test_produce_report_returns_topic(self):
        agent = ResearcherAgent(name="R", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        report = await agent.produce_report("AI", buyer_wallet="wallet_buyer")
        assert report["topic"] == "AI"

    async def test_produce_report_has_key_points(self):
        agent = ResearcherAgent(name="R", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        report = await agent.produce_report("Robotics", buyer_wallet="wallet_buyer")
        assert isinstance(report["key_points"], list)
        assert len(report["key_points"]) >= 1

    async def test_produce_report_has_sources(self):
        agent = ResearcherAgent(name="R", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        report = await agent.produce_report("Climate", buyer_wallet="wallet_buyer")
        assert isinstance(report["sources"], list)

    async def test_produce_report_price_paid(self):
        agent = ResearcherAgent(name="R", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        report = await agent.produce_report("Energy", buyer_wallet="wallet_buyer")
        assert report["price_paid"] == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# WriterAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestWriterAgent:
    async def test_register_sets_resource_id(self):
        agent = _mock_agent(
            WriterAgent,
            [httpx.Response(201, json={**RESOURCE_RESPONSE, "id": "res_writer"})],
        )
        await agent.register()
        assert agent.resource_id == "res_writer"

    async def test_buy_research_returns_receipt(self):
        agent = _mock_agent(
            WriterAgent,
            [httpx.Response(201, json=PAYMENT_RESPONSE)],
        )
        receipt = await agent.buy_research("res_001")
        assert receipt["payment_id"] == "pay_abc123"

    async def test_produce_content_returns_title(self):
        agent = WriterAgent(name="W", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        research = {
            "topic": "Quantum Computing",
            "summary": "A brief summary.",
            "key_points": ["Point one.", "Point two."],
        }
        content = await agent.produce_content(research, buyer_wallet="wallet_pub")
        assert "Quantum Computing" in content["title"]

    async def test_produce_content_has_body(self):
        agent = WriterAgent(name="W", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        research = {"topic": "Space", "summary": "Space is big.", "key_points": ["Stars."]}
        content = await agent.produce_content(research, buyer_wallet="wallet_pub")
        assert len(content["body"]) > 0

    async def test_produce_content_word_count_positive(self):
        agent = WriterAgent(name="W", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        research = {"topic": "Biotech", "summary": "Growing fast.", "key_points": ["CRISPR."]}
        content = await agent.produce_content(research, buyer_wallet="wallet_pub")
        assert content["word_count"] > 0


# ---------------------------------------------------------------------------
# EditorAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEditorAgent:
    async def test_register_sets_resource_id(self):
        agent = _mock_agent(
            EditorAgent,
            [httpx.Response(201, json={**RESOURCE_RESPONSE, "id": "res_editor"})],
        )
        await agent.register()
        assert agent.resource_id == "res_editor"

    async def test_edit_content_adds_edits_list(self):
        agent = EditorAgent(name="E", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        content = {
            "topic": "Testing",
            "title": "Test Title",
            "body": "# test heading\n\nSome body  text.",
            "word_count": 5,
            "produced_by": "Writer",
        }
        edited = await agent.edit_content(content, buyer_wallet="wallet_pub")
        assert isinstance(edited["edits_applied"], list)

    async def test_edit_content_returns_body(self):
        agent = EditorAgent(name="E", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        content = {"topic": "X", "title": "Title", "body": "Body text.", "word_count": 2}
        edited = await agent.edit_content(content, buyer_wallet="wallet_pub")
        assert "Body text." in edited["body"]


# ---------------------------------------------------------------------------
# TranslatorAgent tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTranslatorAgent:
    async def test_register_sets_resource_id(self):
        agent = _mock_agent(
            TranslatorAgent,
            [httpx.Response(201, json={**RESOURCE_RESPONSE, "id": "res_translator"})],
        )
        await agent.register()
        assert agent.resource_id == "res_translator"

    async def test_translate_content_sets_language(self):
        agent = TranslatorAgent(name="T", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        content = {"topic": "AI", "title": "AI Article", "body": "Some content.", "produced_by": "Writer"}
        translated = await agent.translate_content(content, "Spanish", buyer_wallet="wallet_pub")
        assert translated["language"] == "Spanish"

    async def test_translate_content_title_prefixed(self):
        agent = TranslatorAgent(name="T", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        content = {"topic": "AI", "title": "AI Article", "body": "Content.", "produced_by": "Writer"}
        translated = await agent.translate_content(content, "French", buyer_wallet="wallet_pub")
        assert "[French]" in translated["title"]

    async def test_translate_content_body_not_empty(self):
        agent = TranslatorAgent(name="T", api_key=FAKE_API_KEY, agent_wallet=FAKE_WALLET)
        content = {"topic": "Climate", "title": "Climate", "body": "Hot.", "produced_by": "Writer"}
        translated = await agent.translate_content(content, "German", buyer_wallet="wallet_pub")
        assert len(translated["body"]) > 0
