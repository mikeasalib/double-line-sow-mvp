"""
SOW Decomposition Engine — CLI entry point.

Usage:
    python -m src.main --input samples/mock_sow_workspace.txt --format all
    python -m src.main --input path/to/sow.pdf --format jira
    python -m src.main --input path/to/sow.pdf --format markdown
"""
import argparse
import sys
import os

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .ingest import ingest
from .parser import parse_sow, parsed_sow_to_dict
from .matcher import load_catalog, match_deliverables
from .estimator import estimate_tasks
from .dependency import resolve_dependencies
from .exporter import export_jira_csv, export_markdown, export_json


console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="SOW Decomposition Engine — Convert Statements of Work into structured project plans"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to SOW file (text or PDF) or raw SOW text",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["jira", "markdown", "json", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="output",
        help="Output directory (default: output/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed processing information",
    )
    args = parser.parse_args()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error:[/red] ANTHROPIC_API_KEY environment variable not set.")
        console.print("Set it with: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    console.print(Panel("Double Line — SOW Decomposition Engine", style="bold blue"))

    # Step 1: Ingest
    console.print("\n[bold]1. Ingesting SOW...[/bold]")
    try:
        sow_text = ingest(args.input)
        console.print(f"   ✓ Read {len(sow_text)} characters from {args.input}")
    except Exception as e:
        console.print(f"   [red]✗ Ingestion failed: {e}[/red]")
        sys.exit(1)

    # Step 2: Parse with Claude API
    console.print("\n[bold]2. Parsing SOW with Claude API...[/bold]")
    try:
        parsed = parse_sow(sow_text)
        ctx = parsed.client_context
        console.print(f"   ✓ Client: {ctx.organization_name}")
        console.print(f"   ✓ Users: {ctx.user_count}")
        console.print(f"   ✓ Deliverables found: {len(parsed.deliverables)}")
        console.print(f"   ✓ Exclusions found: {len(parsed.exclusions)}")
        console.print(f"   ✓ Federal engagement: {'Yes' if ctx.is_federal else 'No'}")
    except Exception as e:
        console.print(f"   [red]✗ Parsing failed: {e}[/red]")
        sys.exit(1)

    # Step 3: Match against catalog
    console.print("\n[bold]3. Matching deliverables to task catalog...[/bold]")
    catalog = load_catalog()
    match_result = match_deliverables(
        deliverables=parsed.deliverables,
        exclusions=parsed.exclusions,
        catalog=catalog,
        is_federal=ctx.is_federal,
    )
    console.print(f"   ✓ Matched tasks: {len(match_result.matched_tasks)}")
    console.print(f"   ✓ Unmatched deliverables: {len(match_result.unmatched_deliverables)}")
    console.print(f"   ✓ Excluded tasks: {len(match_result.excluded_tasks)}")

    if match_result.unmatched_deliverables:
        console.print("\n   [yellow]Unmatched deliverables (need manual task creation):[/yellow]")
        for d in match_result.unmatched_deliverables:
            console.print(f"   ⚠ {d.name}: {d.description[:80]}")

    # Step 4: Estimate
    console.print("\n[bold]4. Estimating hours...[/bold]")
    estimated = estimate_tasks(match_result.matched_tasks, ctx)

    # Step 5: Resolve dependencies
    console.print("\n[bold]5. Resolving dependencies...[/bold]")
    plan = resolve_dependencies(estimated)
    console.print(f"   ✓ Total estimated hours: {plan.total_hours:.0f}h")
    console.print(f"   ✓ Critical path length: {len(plan.critical_path)} tasks")

    if plan.dependency_warnings:
        for w in plan.dependency_warnings:
            console.print(f"   [yellow]⚠ {w}[/yellow]")

    # Summary table
    if args.verbose:
        console.print("\n")
        table = Table(title="Task Summary", show_lines=True)
        table.add_column("Phase", style="cyan")
        table.add_column("Task", style="white")
        table.add_column("Role", style="green")
        table.add_column("Hours", justify="right", style="yellow")
        table.add_column("Confidence", justify="center")
        table.add_column("Critical", justify="center")

        for task in plan.ordered_tasks:
            conf_color = "green" if task.confidence == "high" else "yellow" if task.confidence == "medium" else "red"
            critical = "⚡" if task.task_id in plan.critical_path else ""
            table.add_row(
                task.phase,
                task.task_name,
                task.role,
                f"{task.adjusted_hours:.0f}",
                f"[{conf_color}]{task.confidence}[/{conf_color}]",
                critical,
            )

        console.print(table)

    # Step 6: Export
    console.print(f"\n[bold]6. Exporting ({args.format})...[/bold]")
    output_dir = args.output_dir

    if args.format in ("jira", "all"):
        path = export_jira_csv(plan, f"{output_dir}/jira_import.csv")
        console.print(f"   ✓ JIRA CSV: {path}")

    if args.format in ("markdown", "all"):
        path = export_markdown(plan, ctx, f"{output_dir}/project_timeline.md")
        console.print(f"   ✓ Markdown: {path}")

    if args.format in ("json", "all"):
        path = export_json(plan, ctx, f"{output_dir}/plan.json")
        console.print(f"   ✓ JSON: {path}")

    console.print("\n[bold green]Done.[/bold green]\n")


if __name__ == "__main__":
    main()
