# src/postmortem_dbt/cli.py

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from .core.llm import generate_dbt_test
from .dbt.writer import write_test

app = typer.Typer(help="Generate dbt tests from plain-English incident postmortems.")
console = Console()

@app.command()
def generate(
    incident: Path = typer.Option(..., "--incident", "-i", help="Path to the incident postmortem markdown file."),
    project: Path = typer.Option(..., "--project", "-p", help="Path to the root of your dbt project."),
    models: str = typer.Option(None, "--models", "-m", help="Comma-separated list of specific dbt models to provide as context (optional)."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview changes without writing to files."),
):
    """
    Analyze an incident and generate a dbt test.
    """
    console.print(Panel.fit(f"🔍 Analyzing Incident: [bold cyan]{incident.name}[/bold cyan]", border_style="blue"))

    if not incident.exists():
        console.print(f"[red]❌ Error:[/red] Incident file not found at {incident}")
        raise typer.Exit(code=1)

    incident_text = incident.read_text(encoding="utf-8")
    target_models = [m.strip() for m in models.split(",")] if models else None

    try:
        with console.status("[bold green]Consulting the LLM...", spinner="dots"):
            proposal = generate_dbt_test(
                incident_text=incident_text,
                project_path=project,
                target_models=target_models
            )

        console.print("\n[bold]✅ Incident Summary:[/bold]", proposal.incident_summary)
        console.print("[bold]🔍 Root Cause:[/bold]", proposal.root_cause)
        console.print(f"[bold]🎯 Target:[/bold] {proposal.target_table}.{proposal.target_column or '(table level)'}")
        console.print(f"[bold]📝 Test Type:[/bold] {proposal.test_type.upper()}")
        console.print("[bold]💡 Rationale:[/bold]", proposal.rationale)
        
        console.print("\n[bold]--- Generated dbt Test Code ---[/bold]")
        console.print(f"[cyan]{proposal.test_code}[/cyan]")
        console.print("[bold]---------------------------------[/bold]\n")

        if project:
            action = "[DRY RUN] Would write to" if dry_run else "Writing to"
            console.print(f"[bold yellow]⚙️  {action} dbt project at: {project}[/bold yellow]")
            write_test(proposal, project_path=project, dry_run=dry_run)
        else:
            console.print("[yellow]⚠️  No --project path provided. Skipping file write.[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ An error occurred:[/red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()