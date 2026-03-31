"""
Simple pipeline example: Researcher → Writer → Publisher.

Demonstrates the most minimal economy possible — no editing or translation,
just research feeding directly into writing, with the Publisher orchestrating.

Usage:
    MAINLAYER_API_KEY=your_key python examples/simple_pipeline.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

# Allow running from the project root without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.agents.publisher import PublisherAgent, PublishedPackage
from src.agents.editor import EditorAgent

console = Console()

TOPIC = "Sustainable Agriculture"
API_KEY = os.environ.get("MAINLAYER_API_KEY", "demo_key_replace_me")


async def run_simple_pipeline() -> PublishedPackage:
    console.print(
        Panel.fit(
            "[bold cyan]Simple Pipeline Example[/bold cyan]\n"
            f"[dim]Researcher → Writer → Publisher | Topic: {TOPIC}[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Instantiate only the three agents needed for this simplified pipeline
    researcher = ResearcherAgent(
        name="Researcher",
        api_key=API_KEY,
        agent_wallet="wallet_researcher_simple",
    )
    writer = WriterAgent(
        name="Writer",
        api_key=API_KEY,
        agent_wallet="wallet_writer_simple",
    )
    editor = EditorAgent(
        name="Editor",
        api_key=API_KEY,
        agent_wallet="wallet_editor_simple",
    )
    publisher = PublisherAgent(
        name="Publisher",
        api_key=API_KEY,
        agent_wallet="wallet_publisher_simple",
    )

    try:
        # Step 1 — Register services
        console.print("[bold]Step 1:[/bold] Registering services on Mainlayer…")
        await asyncio.gather(
            researcher.register(),
            writer.register(),
            editor.register(),
            publisher.register(),
        )
        console.print(
            f"  Researcher resource_id = [cyan]{researcher.resource_id}[/cyan]\n"
            f"  Writer     resource_id = [cyan]{writer.resource_id}[/cyan]\n"
            f"  Editor     resource_id = [cyan]{editor.resource_id}[/cyan]\n"
            f"  Publisher  resource_id = [cyan]{publisher.resource_id}[/cyan]"
        )
        console.print()

        # Step 2 — Run the pipeline (no translation in this example)
        console.print(f"[bold]Step 2:[/bold] Running pipeline for topic=[italic]{TOPIC}[/italic]…")
        package = await publisher.run_pipeline(
            topic=TOPIC,
            researcher=researcher,
            writer=writer,
            editor=editor,
            translators=[],  # Simple pipeline: skip translation
        )

        # Step 3 — Display results
        console.print()
        console.print(Rule("[bold green]Pipeline complete[/bold green]"))
        console.print()
        console.print(f"[bold]Research summary:[/bold]\n  {package.research['summary']}")
        console.print()
        console.print(f"[bold]Article title:[/bold] {package.content['title']}")
        console.print(f"[bold]Word count after editing:[/bold] {package.edited['word_count']}")
        console.print()
        console.print(
            Panel(
                f"[bold yellow]Payments executed:[/bold yellow] {len(package.payment_receipts)}\n"
                f"[bold yellow]Total spent:      [/bold yellow] ${package.total_spent:.4f}",
                border_style="yellow",
                expand=False,
            )
        )

        return package

    finally:
        await asyncio.gather(
            researcher.close(),
            writer.close(),
            editor.close(),
            publisher.close(),
        )


if __name__ == "__main__":
    if API_KEY == "demo_key_replace_me":
        console.print(
            "[yellow]Warning:[/yellow] MAINLAYER_API_KEY not set — "
            "API calls will fail against production.\n"
        )
    asyncio.run(run_simple_pipeline())
