"""Writer agent — buys research ($0.10) and sells written content ($0.05 each)."""

from __future__ import annotations

import logging
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

RESOURCE_SLUG = "written-content"
RESOURCE_PRICE = 0.05
RESOURCE_DESCRIPTION = (
    "Polished written content (article, blog post, or report section) "
    "based on verified research. Ready for editing or publication."
)


class WriterAgent(BaseAgent):
    """
    Purchases research from ResearcherAgent and sells written content.

    Responsibilities:
    - Register the ``written-content`` Mainlayer resource on startup.
    - Pay ResearcherAgent for a research report.
    - Produce written content derived from that research.
    """

    SERVICE_SLUG: str = RESOURCE_SLUG
    SERVICE_PRICE: float = RESOURCE_PRICE

    async def register(self) -> dict:
        """Register the written-content resource on Mainlayer."""
        return await self.setup_service(
            slug=RESOURCE_SLUG,
            price=RESOURCE_PRICE,
            description=RESOURCE_DESCRIPTION,
        )

    async def buy_research(self, researcher_resource_id: str) -> dict:
        """
        Pay the Researcher agent and return the payment receipt.

        Args:
            researcher_resource_id: Resource ID exposed by ResearcherAgent.

        Returns:
            Payment receipt from Mainlayer.
        """
        logger.info("'%s' purchasing research (resource_id=%s)", self.name, researcher_resource_id)
        return await self.pay_for_service(researcher_resource_id)

    async def produce_content(
        self,
        research: dict[str, Any],
        buyer_wallet: str,
    ) -> dict[str, Any]:
        """
        Produce written content from a research report.

        Args:
            research:      The dict returned by ResearcherAgent.produce_report().
            buyer_wallet:  Wallet of the agent that paid for this content.

        Returns:
            A dict with keys: ``title``, ``body``, ``word_count``, ``topic``.
        """
        topic = research.get("topic", "Unknown Topic")
        summary = research.get("summary", "")
        key_points = research.get("key_points", [])

        logger.info("'%s' producing content on topic='%s' for buyer=%s", self.name, topic, buyer_wallet)

        bullet_section = "\n".join(f"- {point}" for point in key_points)
        body = (
            f"# {topic}: An In-Depth Overview\n\n"
            f"## Introduction\n\n"
            f"{summary}\n\n"
            f"## Key Insights\n\n"
            f"{bullet_section}\n\n"
            f"## Conclusion\n\n"
            f"The landscape around {topic} continues to shift. "
            "Organisations that act on these insights early will gain a durable competitive edge."
        )

        return {
            "title": f"{topic}: An In-Depth Overview",
            "topic": topic,
            "body": body,
            "word_count": len(body.split()),
            "based_on_research": research.get("produced_by"),
            "produced_by": self.name,
            "price_paid": RESOURCE_PRICE,
        }
