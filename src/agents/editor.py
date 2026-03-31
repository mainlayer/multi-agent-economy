"""Editor agent — buys written content ($0.05) and sells editing ($0.03 each)."""

from __future__ import annotations

import logging
import re
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

RESOURCE_SLUG = "edited-content"
RESOURCE_PRICE = 0.03
RESOURCE_DESCRIPTION = (
    "Professionally edited content: grammar-checked, restructured for clarity, "
    "and optimised for reader engagement."
)


class EditorAgent(BaseAgent):
    """
    Purchases written content from WriterAgent and sells edited versions.

    Responsibilities:
    - Register the ``edited-content`` Mainlayer resource on startup.
    - Pay WriterAgent for written content.
    - Return a polished, edited artefact.
    """

    SERVICE_SLUG: str = RESOURCE_SLUG
    SERVICE_PRICE: float = RESOURCE_PRICE

    async def register(self) -> dict:
        """Register the edited-content resource on Mainlayer."""
        return await self.setup_service(
            slug=RESOURCE_SLUG,
            price=RESOURCE_PRICE,
            description=RESOURCE_DESCRIPTION,
        )

    async def buy_content(self, writer_resource_id: str) -> dict:
        """
        Pay the Writer agent for written content.

        Args:
            writer_resource_id: Resource ID exposed by WriterAgent.

        Returns:
            Payment receipt from Mainlayer.
        """
        logger.info("'%s' purchasing written content (resource_id=%s)", self.name, writer_resource_id)
        return await self.pay_for_service(writer_resource_id)

    async def edit_content(
        self,
        content: dict[str, Any],
        buyer_wallet: str,
    ) -> dict[str, Any]:
        """
        Edit and polish a piece of written content.

        Applies lightweight deterministic edits for demo purposes.
        A production implementation would call an LLM editor.

        Args:
            content:       Dict returned by WriterAgent.produce_content().
            buyer_wallet:  Wallet of the agent that paid for editing.

        Returns:
            A dict with keys: ``title``, ``body``, ``edits_applied``, ``topic``.
        """
        topic = content.get("topic", "Unknown Topic")
        body: str = content.get("body", "")
        title: str = content.get("title", "Untitled")

        logger.info("'%s' editing content on topic='%s' for buyer=%s", self.name, topic, buyer_wallet)

        edits: list[str] = []

        # Normalise whitespace
        edited_body = re.sub(r" {2,}", " ", body)
        if edited_body != body:
            edits.append("Normalised whitespace")

        # Ensure consistent heading style (capitalise first letter)
        def capitalise_heading(m: re.Match) -> str:
            heading_text = m.group(1)
            return f"# {heading_text[0].upper() + heading_text[1:]}"

        edited_body_v2 = re.sub(r"^# (.+)$", capitalise_heading, edited_body, flags=re.MULTILINE)
        if edited_body_v2 != edited_body:
            edits.append("Standardised heading capitalisation")
        edited_body = edited_body_v2

        # Append editorial note
        editorial_note = (
            "\n\n---\n*Edited by the Editor agent for clarity and readability.*"
        )
        edited_body += editorial_note
        edits.append("Added editorial attribution note")

        return {
            "title": title,
            "topic": topic,
            "body": edited_body,
            "word_count": len(edited_body.split()),
            "edits_applied": edits,
            "original_word_count": content.get("word_count", 0),
            "based_on": content.get("produced_by"),
            "produced_by": self.name,
            "price_paid": RESOURCE_PRICE,
        }
