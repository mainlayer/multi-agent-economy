"""
Entry point for the multi-agent economy demo.

Run with:
    python -m src.main

Or via the installed CLI:
    multi-agent-economy
"""

from __future__ import annotations

import asyncio
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from .economy import AgentEconomy, EconomyConfig, EconomyStats
from .agents.publisher import PublishedPackage

console = Console()

DEMO_TOPICS = [
    "Artificial Intelligence in Healthcare",
    "Renewable Energy Markets",
]

TRANSLATION_LANGUAGE = "Spanish"


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_header() -> None:
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Multi-Agent Economy[/bold cyan]\n"
            "[dim]AI agents paying each other for services via Mainlayer[/dim]",
            border_style="cyan",
        )
    )
    console.print()


def _print_agent_table() -> None:
    table = Table(title="Economy Agents", box=box.ROUNDED, show_header=True)
    table.add_column("Agent", style="bold")
    table.add_column("Sells", style="green")
    table.add_column("Price", justify="right", style="yellow")
    table.add_column("Buys From", style="cyan")

    table.add_row("Researcher", "Research Reports",   "$0.10", "—")
    table.add_row("Writer",     "Written Content",    "$0.05", "Researcher")
    table.add_row("Editor",     "Edited Content",     "$0.03", "Writer")
    table.add_row("Translator", "Translations",       "$0.04", "Writer")
    table.add_row("Publisher",  "Published Packages", "$0.20", "All of the above")

    console.print(table)
    console.print()


def _print_package(package: PublishedPackage, index: int) -> None:
    console.print(Rule(f"[bold]Pipeline #{index} — {package.topic}[/bold]"))
    console.print()

    # Payment flow table
    payment_table = Table(title="Payment Flow", box=box.SIMPLE_HEAD, show_header=True)
    payment_table.add_column("Step", style="dim")
    payment_table.add_column("Payment ID", style="cyan")
    payment_table.add_column("Status", style="green")

    for receipt in package.payment_receipts:
        step = receipt.get("step", "—")
        pid = receipt.get("payment_id", receipt.get("id", "—"))
        status = receipt.get("status", "confirmed")
        payment_table.add_row(step, str(pid), str(status))

    console.print(payment_table)

    # Research summary
    console.print()
    console.print("[bold]Research Summary:[/bold]")
    console.print(Text(package.research.get("summary", ""), style="dim"))

    # Content title
    console.print()
    console.print(f"[bold]Written Article:[/bold] {package.content.get('title', '')}")
    console.print(f"  [dim]{package.edited.get('word_count', 0)} words after editing[/dim]")

    # Translations
    if package.translations:
        console.print()
        console.print("[bold]Translations:[/bold]")
        for lang, trans in package.translations.items():
            console.print(f"  [{lang}] {trans.get('title', '')}")

    # Cost
    console.print()
    console.print(
        Panel(
            f"[bold yellow]Total pipeline cost: ${package.total_spent:.4f}[/bold yellow]\n"
            f"Payments executed: {len(package.payment_receipts)}",
            border_style="yellow",
            expand=False,
        )
    )
    console.print()


def _print_economy_stats(stats: EconomyStats) -> None:
    console.print(Rule("[bold cyan]Economy Summary[/bold cyan]"))
    console.print()

    summary_table = Table(box=box.ROUNDED, show_header=False)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", style="cyan", justify="right")

    summary_table.add_row("Topics processed",  str(stats.topics_processed))
    summary_table.add_row("Total payments",    str(stats.total_payments))
    summary_table.add_row("Total USD spent",   f"${stats.total_spent:.4f}")

    console.print(summary_table)
    console.print()


# ---------------------------------------------------------------------------
# Main async entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    api_key = os.environ.get("MAINLAYER_API_KEY", "demo_key_replace_me")

    if api_key == "demo_key_replace_me":
        console.print(
            "[yellow]Warning:[/yellow] MAINLAYER_API_KEY not set. "
            "Using placeholder key — API calls will fail against production.\n"
            "Set the environment variable to run against the live Mainlayer API.\n"
        )

    config = EconomyConfig(api_key=api_key)

    _print_header()
    _print_agent_table()

    console.print("[bold]Starting economy — registering all agent services…[/bold]")

    async with AgentEconomy(config) as economy:
        console.print("[green]All agents registered.[/green]\n")

        for i, topic in enumerate(DEMO_TOPICS, start=1):
            console.print(f"[bold cyan]Running pipeline {i}/{len(DEMO_TOPICS)} — topic:[/bold cyan] {topic}")

            try:
                package = await economy.run_topic(
                    topic=topic,
                    include_translation=True,
                    target_language=TRANSLATION_LANGUAGE,
                )
                _print_package(package, index=i)

            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Pipeline failed for '{topic}': {exc}[/red]")

        _print_economy_stats(economy.stats)

    console.print("[bold green]Demo complete.[/bold green]")


def run() -> None:
    """Synchronous entry point (used by the CLI script)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    run()
