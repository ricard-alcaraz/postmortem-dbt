# src/postmortem_dbt/cli.py
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from .core.llm import generate_dbt_tests, get_retry_stats
from .dbt.writer import write_test
from .dbt.manifest import DbtManifest

app = typer.Typer(help="Generate dbt tests from plain-English incident postmortems.", add_completion=False)
console = Console()

@app.command()
def generate(
    incident: Path = typer.Option(..., "--incident", "-i", help="Path to the incident postmortem markdown file."),
    project: Path = typer.Option(..., "--project", "-p", help="Path to the root of your dbt project."),
    models: str = typer.Option(None, "--models", "-m", help="Comma-separated list of specific dbt models to provide as context (optional)."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt and write directly to disk."),
):
    """Analyze an incident and generate dbt tests."""
    console.print(Panel.fit(f"🔍 Analyzing Incident: [bold cyan]{incident.name}[/bold cyan]", border_style="blue"))

    if not incident.exists():
        console.print(f"[red]❌ Error:[/red] Incident file not found at {incident}")
        raise typer.Exit(code=1)

    manifest_path = project / "target" / "manifest.json"
    if not manifest_path.exists():
        console.print(f"[red]❌ Error:[/red] dbt manifest not found at {manifest_path}. Run `dbt compile` first.")
        raise typer.Exit(code=1)

    incident_text = incident.read_text(encoding="utf-8")
    target_models = [m.strip() for m in models.split(",")] if models else None

    try:
        with console.status("[bold green]Consulting the LLM...", spinner="dots"):
            proposals = generate_dbt_tests(
                incident_text=incident_text,
                project_path=project,
                target_models=target_models
            )

        testable_proposals = [p for p in proposals if p.testable]
        
        if not testable_proposals:
            console.print("[yellow]⚠️  The LLM determined this incident is not testable via dbt (e.g., infrastructure/vendor issue). No tests generated.[/yellow]")
            raise typer.Exit(code=0)

        for i, proposal in enumerate(testable_proposals, 1):
            console.print(f"\n[bold]--- Proposal {i} (Confidence: {proposal.confidence:.0%}) ---[/bold]")
            console.print("[bold]✅ Incident Summary:[/bold]", proposal.incident_summary)
            console.print("[bold]🔍 Root Cause:[/bold]", proposal.root_cause)
            console.print(f"[bold]🎯 Target:[/bold] {proposal.target_table}.{proposal.target_column or '(table level)'}")
            console.print(f"[bold]📝 Test Type:[/bold] {proposal.test_type.upper()}")
            console.print("[bold]💡 Rationale:[/bold]", proposal.rationale)
            console.print("[bold]--- Generated dbt Test Code ---[/bold]")
            console.print(f"[cyan]{proposal.test_code}[/cyan]")
            console.print("[bold]---------------------------------[/bold]")

        manifest = DbtManifest(manifest_path)
        
        if not yes:
            confirm = typer.confirm(f"Write these {len(testable_proposals)} test(s) to your dbt project?", default=False)
            if not confirm:
                console.print("[yellow]⚠️  Aborted. No files were modified.[/yellow]")
                raise typer.Exit(code=0)

        console.print(f"[bold yellow]⚙️  Writing to dbt project at: {project}[/bold yellow]")
        for proposal in testable_proposals:
            write_test(proposal, project_path=project, manifest=manifest, dry_run=False)
            
        console.print("[green]🎉 Done! Run `dbt test` to verify.[/green]")
        
        # Log retry stats
        stats = get_retry_stats()
        if stats['attempts'] > 0:
            rescue_rate = (stats['rescued_by_retry'] / stats['attempts']) * 100
            console.print(f"[dim]📊 LLM Stats: {stats['attempts']} total attempts, {rescue_rate:.1f}% rescued by retry loop.[/dim]")

    except FileExistsError as e:
        console.print(f"[red]❌ File Error:[/red] {e}")
        raise typer.Exit(code=1)
    except ValueError as e:
        console.print(f"[red]❌ Validation Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ An unexpected error occurred:[/red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()