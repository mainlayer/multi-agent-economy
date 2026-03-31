"""
Competitive economy example: Multiple writers competing for research.

Two WriterAgents simultaneously purchase research from a single ResearcherAgent,
then each produce their own content. A single Publisher buys from both and
chooses the higher word-count article for final publication.

This demonstrates:
- Multiple buyers purchasing the same Mainlayer resource
- Concurrent payment flows
- Competitive dynamics between agents

Usage:
    MAINLAYER_API_KEY=your_key python examples/competitive_economy.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich import box

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.agents.editor import EditorAgent
from src.agents.publisher import PublisherAgent, PublishedPackage

console = Console()

TOPIC = "Future of Remote Work"
API_KEY = os.environ.get("MAINLAYER_API_KEY", "demo_key_replace_me")


async def run_competitive_economy() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Competitive Economy Example[/bold cyan]\n"
            "[dim]Two writers compete for the same research — "
            "Publisher picks the best.[/dim]\n"
            f"[dim]Topic: {TOPIC}[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Shared Researcher — sells the same research resource to both writers
    researcher = ResearcherAgent(
        name="Researcher",
        api_key=API_KEY,
        agent_wallet="wallet_researcher_comp",
    )

    # Two competing Writers
    writer_alpha = WriterAgent(
        name="Writer Alpha",
        api_key=API_KEY,
        agent_wallet="wallet_writer_alpha",
    )
    writer_beta = WriterAgent(
        name="Writer Beta",
        api_key=API_KEY,
        agent_wallet="wallet_writer_beta",
    )

    # Single shared Editor and Publisher
    editor = EditorAgent(
        name="Editor",
        api_key=API_KEY,
        agent_wallet="wallet_editor_comp",
    )
    publisher = PublisherAgent(
        name="Publisher",
        api_key=API_KEY,
        agent_wallet="wallet_publisher_comp",
    )

    try:
        # ── Phase 1: Register all services concurrently ───────────────────
        console.print("[bold]Phase 1:[/bold] Registering services on Mainlayer…")
        await asyncio.gather(
            researcher.register(),
            writer_alpha.register(),
            writer_beta.register(),
            editor.register(),
            publisher.register(),
        )

        reg_table = Table(box=box.SIMPLE, show_header=False)
        reg_table.add_column("Agent", style="bold")
        reg_table.add_column("Resource ID", style="cyan")
        for agent in (researcher, writer_alpha, writer_beta, editor, publisher):
            reg_table.add_row(agent.name, str(agent.resource_id))
        console.print(reg_table)
        console.print()

        # ── Phase 2: Publisher pays Researcher once; both writers buy research ─
        console.print("[bold]Phase 2:[/bold] All three parties purchase research concurrently…")

        receipt_pub_res, receipt_alpha_res, receipt_beta_res = await asyncio.gather(
            publisher.pay_for_service(researcher.resource_id),   # type: ignore[arg-type]
            writer_alpha.buy_research(researcher.resource_id),   # type: ignore[arg-type]
            writer_beta.buy_research(researcher.resource_id),    # type: ignore[arg-type]
        )

        research = await researcher.produce_report(topic=TOPIC, buyer_wallet=publisher.agent_wallet)
        console.print(f"  Research report produced: [green]{research['topic']}[/green]")
        console.print()

        # ── Phase 3: Writers produce content concurrently ─────────────────
        console.print("[bold]Phase 3:[/bold] Both writers produce content simultaneously…")

        content_alpha, content_beta = await asyncio.gather(
            writer_alpha.produce_content(research, buyer_wallet=publisher.agent_wallet),
            writer_beta.produce_content(research, buyer_wallet=publisher.agent_wallet),
        )

        comp_table = Table(title="Writer Output Comparison", box=box.ROUNDED)
        comp_table.add_column("Writer", style="bold")
        comp_table.add_column("Title")
        comp_table.add_column("Words", justify="right", style="yellow")

        comp_table.add_row(
            writer_alpha.name,
            content_alpha["title"],
            str(content_alpha["word_count"]),
        )
        comp_table.add_row(
            writer_beta.name,
            content_beta["title"],
            str(content_beta["word_count"]),
        )
        console.print(comp_table)
        console.print()

        # ── Phase 4: Publisher selects winner ─────────────────────────────
        if content_alpha["word_count"] >= content_beta["word_count"]:
            winner_writer = writer_alpha
            winner_content = content_alpha
            loser_name = writer_beta.name
        else:
            winner_writer = writer_beta
            winner_content = content_beta
            loser_name = writer_alpha.name

        console.print(
            f"[bold]Phase 4:[/bold] Publisher selects "
            f"[green]{winner_writer.name}[/green] "
            f"({winner_content['word_count']} words) "
            f"over [dim]{loser_name}[/dim]."
        )
        console.print()

        # Publisher pays the winner
        receipt_pub_writer = await publisher.pay_for_service(winner_writer.resource_id)  # type: ignore[arg-type]

        # ── Phase 5: Editor polishes the winning content ───────────────────
        console.print("[bold]Phase 5:[/bold] Editor edits the winning content…")

        receipt_editor_buys = await editor.buy_content(winner_writer.resource_id)  # type: ignore[arg-type]
        edited = await editor.edit_content(winner_content, buyer_wallet=publisher.agent_wallet)
        receipt_pub_editor = await publisher.pay_for_service(editor.resource_id)  # type: ignore[arg-type]

        # ── Summary ───────────────────────────────────────────────────────
        console.print()
        console.print(Rule("[bold green]Competition complete[/bold green]"))
        console.print()

        total_payments = 8  # approximate count across all concurrent flows
        console.print(
            Panel(
                f"[bold]Winner:[/bold]        {winner_writer.name}\n"
                f"[bold]Final title:[/bold]   {edited['title']}\n"
                f"[bold]Final words:[/bold]   {edited['word_count']}\n"
                f"[bold]Edits applied:[/bold] {', '.join(edited['edits_applied'])}",
                title="Publication Result",
                border_style="green",
            )
        )

    finally:
        await asyncio.gather(
            researcher.close(),
            writer_alpha.close(),
            writer_beta.close(),
            editor.close(),
            publisher.close(),
        )


if __name__ == "__main__":
    if API_KEY == "demo_key_replace_me":
        console.print(
            "[yellow]Warning:[/yellow] MAINLAYER_API_KEY not set — "
            "API calls will fail against production.\n"
        )
    asyncio.run(run_competitive_economy())
