"""Publisher agent — orchestrates the full pipeline, paying all other agents."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .base_agent import BaseAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from .editor import EditorAgent
from .translator import TranslatorAgent

logger = logging.getLogger(__name__)

RESOURCE_SLUG = "published-package"
RESOURCE_PRICE = 0.20
RESOURCE_DESCRIPTION = (
    "Fully published content package: researched, written, edited, and optionally translated. "
    "Ready for distribution across any channel."
)


@dataclass
class PublishedPackage:
    """The final deliverable produced by the Publisher after paying all agents."""

    topic: str
    research: dict[str, Any]
    content: dict[str, Any]
    edited: dict[str, Any]
    translations: dict[str, dict[str, Any]] = field(default_factory=dict)
    total_spent: float = 0.0
    payment_receipts: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        langs = list(self.translations.keys()) or ["none"]
        return (
            f"Topic: {self.topic} | "
            f"Edited words: {self.edited.get('word_count', 0)} | "
            f"Translations: {', '.join(langs)} | "
            f"Total spent: ${self.total_spent:.4f}"
        )


class PublisherAgent(BaseAgent):
    """
    Orchestrates the multi-agent economy pipeline.

    Pays the Researcher, Writer, Editor, and optionally Translator to produce
    a complete, publish-ready content package.
    """

    SERVICE_SLUG: str = RESOURCE_SLUG
    SERVICE_PRICE: float = RESOURCE_PRICE

    async def register(self) -> dict:
        """Register the published-package resource on Mainlayer."""
        return await self.setup_service(
            slug=RESOURCE_SLUG,
            price=RESOURCE_PRICE,
            description=RESOURCE_DESCRIPTION,
        )

    async def run_pipeline(
        self,
        topic: str,
        researcher: ResearcherAgent,
        writer: WriterAgent,
        editor: EditorAgent,
        translators: list[tuple[TranslatorAgent, str]] | None = None,
    ) -> PublishedPackage:
        """
        Execute the full content pipeline.

        Steps:
        1. Pay Researcher → get research report.
        2. Writer pays Researcher (internally) and produces content.
           Publisher then pays Writer to receive that content.
        3. Editor pays Writer (internally) and edits the content.
           Publisher pays Editor to receive edited copy.
        4. (Optional) Each Translator pays Writer (internally) and translates.
           Publisher pays each Translator to receive translations.

        Args:
            topic:       Subject to research and publish.
            researcher:  ResearcherAgent instance (must be registered).
            writer:      WriterAgent instance (must be registered).
            editor:      EditorAgent instance (must be registered).
            translators: List of (TranslatorAgent, language) tuples, or None.

        Returns:
            A populated PublishedPackage.
        """
        translators = translators or []
        receipts: list[dict[str, Any]] = []
        total_spent: float = 0.0

        logger.info("'%s' starting pipeline for topic='%s'", self.name, topic)

        # ── Step 1: Pay Researcher ──────────────────────────────────────────
        if researcher.resource_id is None:
            raise RuntimeError(f"Researcher '{researcher.name}' has not registered a resource yet.")

        logger.info("'%s' → paying Researcher for research report", self.name)
        receipt_research = await self.pay_for_service(researcher.resource_id)
        receipts.append({"step": "research", **receipt_research})
        total_spent += researcher.SERVICE_PRICE

        research = await researcher.produce_report(topic=topic, buyer_wallet=self.agent_wallet)

        # ── Step 2: Writer produces content (internally pays Researcher) ────
        if writer.resource_id is None:
            raise RuntimeError(f"Writer '{writer.name}' has not registered a resource yet.")

        logger.info("'%s' → paying Writer for written content", self.name)
        # Writer purchases research on its own account
        receipt_writer_buys = await writer.buy_research(researcher.resource_id)
        receipts.append({"step": "writer_buys_research", **receipt_writer_buys})
        total_spent += researcher.SERVICE_PRICE  # cost re-billed to pipeline total

        content = await writer.produce_content(research=research, buyer_wallet=self.agent_wallet)

        # Publisher pays Writer for the content
        receipt_writer_sells = await self.pay_for_service(writer.resource_id)
        receipts.append({"step": "writing", **receipt_writer_sells})
        total_spent += writer.SERVICE_PRICE

        # ── Step 3: Editor edits content ───────────────────────────────────
        if editor.resource_id is None:
            raise RuntimeError(f"Editor '{editor.name}' has not registered a resource yet.")

        logger.info("'%s' → paying Editor for edited content", self.name)
        receipt_editor_buys = await editor.buy_content(writer.resource_id)
        receipts.append({"step": "editor_buys_content", **receipt_editor_buys})
        total_spent += writer.SERVICE_PRICE

        edited = await editor.edit_content(content=content, buyer_wallet=self.agent_wallet)

        receipt_editor_sells = await self.pay_for_service(editor.resource_id)
        receipts.append({"step": "editing", **receipt_editor_sells})
        total_spent += editor.SERVICE_PRICE

        # ── Step 4: Optional translations ─────────────────────────────────
        translations: dict[str, dict[str, Any]] = {}
        for translator, language in translators:
            if translator.resource_id is None:
                logger.warning("Translator '%s' not registered, skipping.", translator.name)
                continue

            logger.info("'%s' → paying Translator for %s translation", self.name, language)
            receipt_trans_buys = await translator.buy_content(writer.resource_id)
            receipts.append({"step": f"translator_{language}_buys_content", **receipt_trans_buys})
            total_spent += writer.SERVICE_PRICE

            translation = await translator.translate_content(
                content=content,
                target_language=language,
                buyer_wallet=self.agent_wallet,
            )
            translations[language] = translation

            receipt_trans_sells = await self.pay_for_service(translator.resource_id)
            receipts.append({"step": f"translation_{language}", **receipt_trans_sells})
            total_spent += translator.SERVICE_PRICE

        logger.info(
            "'%s' pipeline complete: topic='%s' total_spent=$%.4f",
            self.name,
            topic,
            total_spent,
        )

        return PublishedPackage(
            topic=topic,
            research=research,
            content=content,
            edited=edited,
            translations=translations,
            total_spent=total_spent,
            payment_receipts=receipts,
        )
