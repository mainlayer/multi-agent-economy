"""Translator agent — buys written content ($0.05) and sells translations ($0.04 each)."""

from __future__ import annotations

import logging
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

RESOURCE_SLUG = "translated-content"
RESOURCE_PRICE = 0.04
RESOURCE_DESCRIPTION = (
    "Professional translation of written content into the target language. "
    "Preserves meaning, tone, and structure."
)

# Stub translations for demo purposes — a real agent would call an LLM or translation API.
_LANGUAGE_GREETINGS: dict[str, str] = {
    "Spanish": "Esta es una traducción al español.",
    "French": "Ceci est une traduction en français.",
    "German": "Dies ist eine Übersetzung auf Deutsch.",
    "Japanese": "これは日本語への翻訳です。",
    "Portuguese": "Esta é uma tradução para o português.",
}
_DEFAULT_TRANSLATED_NOTE = "This is a translated version of the content."


class TranslatorAgent(BaseAgent):
    """
    Purchases written content from WriterAgent and sells translated versions.

    Responsibilities:
    - Register the ``translated-content`` Mainlayer resource on startup.
    - Pay WriterAgent for written content.
    - Return a translated artefact in the requested language.
    """

    SERVICE_SLUG: str = RESOURCE_SLUG
    SERVICE_PRICE: float = RESOURCE_PRICE

    async def register(self) -> dict:
        """Register the translated-content resource on Mainlayer."""
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

    async def translate_content(
        self,
        content: dict[str, Any],
        target_language: str,
        buyer_wallet: str,
    ) -> dict[str, Any]:
        """
        Translate written content into a target language.

        Args:
            content:         Dict returned by WriterAgent.produce_content().
            target_language: Language to translate into (e.g. "Spanish").
            buyer_wallet:    Wallet of the agent that paid for this translation.

        Returns:
            A dict with keys: ``title``, ``body``, ``language``, ``topic``.
        """
        topic = content.get("topic", "Unknown Topic")
        body: str = content.get("body", "")
        title: str = content.get("title", "Untitled")

        logger.info(
            "'%s' translating content on topic='%s' to %s for buyer=%s",
            self.name,
            topic,
            target_language,
            buyer_wallet,
        )

        lang_note = _LANGUAGE_GREETINGS.get(target_language, _DEFAULT_TRANSLATED_NOTE)

        translated_body = (
            f"[{target_language} Translation]\n\n"
            f"{lang_note}\n\n"
            f"---\n\n"
            f"{body}\n\n"
            f"---\n"
            f"*Translated to {target_language} by the Translator agent.*"
        )

        return {
            "title": f"[{target_language}] {title}",
            "topic": topic,
            "body": translated_body,
            "language": target_language,
            "word_count": len(translated_body.split()),
            "original_language": "English",
            "based_on": content.get("produced_by"),
            "produced_by": self.name,
            "price_paid": RESOURCE_PRICE,
        }
