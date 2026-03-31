"""Researcher agent — sells research reports at $0.10 each."""

from __future__ import annotations

import logging
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

RESOURCE_SLUG = "research-report"
RESOURCE_PRICE = 0.10
RESOURCE_DESCRIPTION = (
    "Comprehensive research report on any topic. "
    "Includes key facts, sources, and actionable insights."
)


class ResearcherAgent(BaseAgent):
    """
    Sells research reports to other agents in the economy.

    Responsibilities:
    - Register the ``research-report`` Mainlayer resource on startup.
    - Accept requests from paying agents and return a report dict.
    """

    SERVICE_SLUG: str = RESOURCE_SLUG
    SERVICE_PRICE: float = RESOURCE_PRICE

    async def register(self) -> dict:
        """Register the research-report resource on Mainlayer."""
        return await self.setup_service(
            slug=RESOURCE_SLUG,
            price=RESOURCE_PRICE,
            description=RESOURCE_DESCRIPTION,
        )

    async def produce_report(self, topic: str, buyer_wallet: str) -> dict[str, Any]:
        """
        Produce a research report for a verified buyer.

        In a production system this would call an LLM or a real research pipeline.
        Here we return a deterministic stub that is easy to test.

        Args:
            topic:         Subject to research.
            buyer_wallet:  Wallet of the agent that paid for access.

        Returns:
            A dict with keys: ``topic``, ``summary``, ``key_points``, ``sources``.
        """
        logger.info("'%s' producing report on topic='%s' for buyer=%s", self.name, topic, buyer_wallet)

        return {
            "topic": topic,
            "summary": (
                f"Research report on '{topic}': This domain is evolving rapidly. "
                "Key drivers include technological advancement, shifting consumer "
                "behaviour, and regulatory changes."
            ),
            "key_points": [
                f"{topic} market is projected to grow 25% YoY.",
                "Three dominant players control ~60% of market share.",
                "Regulatory headwinds may reshape competitive dynamics by 2026.",
                "AI-driven automation is the primary efficiency lever.",
            ],
            "sources": [
                f"https://example.com/reports/{topic.lower().replace(' ', '-')}-2024",
                "https://example.com/industry-analysis/global-trends",
            ],
            "produced_by": self.name,
            "price_paid": RESOURCE_PRICE,
        }
