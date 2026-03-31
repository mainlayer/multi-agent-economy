"""AgentEconomy — initialises and coordinates all agents in the economy simulation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from .agents.editor import EditorAgent
from .agents.publisher import PublishedPackage, PublisherAgent
from .agents.researcher import ResearcherAgent
from .agents.translator import TranslatorAgent
from .agents.writer import WriterAgent

logger = logging.getLogger(__name__)


@dataclass
class EconomyConfig:
    """Holds all API keys and wallet addresses needed to bootstrap the economy."""

    api_key: str
    researcher_wallet: str = "wallet_researcher_001"
    writer_wallet: str = "wallet_writer_001"
    editor_wallet: str = "wallet_editor_001"
    translator_wallet: str = "wallet_translator_001"
    publisher_wallet: str = "wallet_publisher_001"


@dataclass
class EconomyStats:
    """Aggregated metrics from a completed economy simulation run."""

    total_payments: int = 0
    total_spent: float = 0.0
    topics_processed: int = 0
    packages: list[PublishedPackage] = field(default_factory=list)

    def add_package(self, package: PublishedPackage) -> None:
        self.packages.append(package)
        self.total_payments += len(package.payment_receipts)
        self.total_spent += package.total_spent
        self.topics_processed += 1

    def summary(self) -> str:
        return (
            f"Topics processed: {self.topics_processed} | "
            f"Total payments: {self.total_payments} | "
            f"Total spent: ${self.total_spent:.4f}"
        )


class AgentEconomy:
    """
    Bootstraps and runs the multi-agent economy.

    Usage::

        economy = AgentEconomy(config)
        await economy.start()
        package = await economy.run_topic("Artificial Intelligence")
        await economy.stop()
    """

    def __init__(self, config: EconomyConfig) -> None:
        self.config = config
        self._running = False

        # Instantiate all five agents
        self.researcher = ResearcherAgent(
            name="Researcher",
            api_key=config.api_key,
            agent_wallet=config.researcher_wallet,
        )
        self.writer = WriterAgent(
            name="Writer",
            api_key=config.api_key,
            agent_wallet=config.writer_wallet,
        )
        self.editor = EditorAgent(
            name="Editor",
            api_key=config.api_key,
            agent_wallet=config.editor_wallet,
        )
        self.translator = TranslatorAgent(
            name="Translator",
            api_key=config.api_key,
            agent_wallet=config.translator_wallet,
        )
        self.publisher = PublisherAgent(
            name="Publisher",
            api_key=config.api_key,
            agent_wallet=config.publisher_wallet,
        )

        self.stats = EconomyStats()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Register all agent services with Mainlayer concurrently.

        This must be called before any call to run_topic() or run_simulation().
        """
        logger.info("AgentEconomy starting — registering all services concurrently…")

        await asyncio.gather(
            self.researcher.register(),
            self.writer.register(),
            self.editor.register(),
            self.translator.register(),
            self.publisher.register(),
        )

        self._running = True
        logger.info("AgentEconomy ready — all agents registered.")

    async def stop(self) -> None:
        """Gracefully shut down all agent HTTP clients."""
        logger.info("AgentEconomy stopping — closing agent connections…")
        await asyncio.gather(
            self.researcher.close(),
            self.writer.close(),
            self.editor.close(),
            self.translator.close(),
            self.publisher.close(),
        )
        self._running = False
        logger.info("AgentEconomy stopped.")

    # ------------------------------------------------------------------
    # Economy operations
    # ------------------------------------------------------------------

    async def run_topic(
        self,
        topic: str,
        include_translation: bool = True,
        target_language: str = "Spanish",
    ) -> PublishedPackage:
        """
        Run the full pipeline for a single topic.

        Args:
            topic:               Subject to research and publish.
            include_translation: Whether to include a translation step.
            target_language:     Language for translation (default: Spanish).

        Returns:
            A PublishedPackage with all artefacts and payment receipts.
        """
        if not self._running:
            raise RuntimeError("Economy is not started. Call await economy.start() first.")

        translators = (
            [(self.translator, target_language)] if include_translation else []
        )

        package = await self.publisher.run_pipeline(
            topic=topic,
            researcher=self.researcher,
            writer=self.writer,
            editor=self.editor,
            translators=translators,
        )

        self.stats.add_package(package)
        return package

    async def run_simulation(
        self,
        topics: list[str],
        include_translation: bool = True,
        target_language: str = "Spanish",
    ) -> EconomyStats:
        """
        Run the pipeline for multiple topics sequentially.

        Args:
            topics:              List of topics to process.
            include_translation: Whether to include translation for each topic.
            target_language:     Language for all translations.

        Returns:
            Aggregated EconomyStats across all topics.
        """
        if not self._running:
            raise RuntimeError("Economy is not started. Call await economy.start() first.")

        for topic in topics:
            logger.info("AgentEconomy processing topic='%s'", topic)
            await self.run_topic(
                topic=topic,
                include_translation=include_translation,
                target_language=target_language,
            )

        return self.stats

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AgentEconomy":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()
