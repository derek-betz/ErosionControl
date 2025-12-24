"""Command-line interface for EC Agent."""

import json
import os
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from ec_agent.llm_adapter import MockLLMAdapter, OpenAIAdapter
from ec_agent.models import ProjectInput, ProjectOutput
from ec_agent.rules_engine import RulesEngine

app = typer.Typer(
    name="ec-agent",
    help="EC Agent - Erosion Control Practices and Pay Items Calculator for Roadway Engineers",
    add_completion=False,
)
console = Console()


def resolve_api_key(cli_value: str | None) -> str | None:
    """Resolve OpenAI API key from CLI, env var, or local file."""
    if cli_value:
        return cli_value

    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    key_file = os.getenv("OPENAI_API_KEY_FILE")
    key_path = Path(key_file) if key_file else Path("API_KEY") / "API_KEY.txt"
    if key_path.is_file():
        key = key_path.read_text(encoding="utf-8").strip()
        return key or None

    return None


def load_project(input_path: Path) -> ProjectInput:
    """Load project data from YAML or JSON file.

    Args:
        input_path: Path to input file

    Returns:
        ProjectInput model
    """
    with open(input_path) as f:
        if input_path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        elif input_path.suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {input_path.suffix}")

    return ProjectInput(**data)


def save_output(output: ProjectOutput, output_path: Path) -> None:
    """Save output to YAML or JSON file.

    Args:
        output: ProjectOutput model
        output_path: Path to output file
    """
    output_dict = output.model_dump(mode="json")

    with open(output_path, "w") as f:
        if output_path.suffix in [".yaml", ".yml"]:
            yaml.safe_dump(output_dict, f, default_flow_style=False, sort_keys=False)
        elif output_path.suffix == ".json":
            json.dump(output_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported file format: {output_path.suffix}")


def print_summary(output: ProjectOutput) -> None:
    """Print a formatted summary of the output.

    Args:
        output: ProjectOutput model
    """
    console.print(f"\n[bold green]EC Agent Results for: {output.project_name}[/bold green]")
    console.print(f"[dim]Generated: {output.timestamp}[/dim]\n")

    # Summary statistics
    summary_table = Table(title="Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="magenta")

    for key, value in output.summary.items():
        if key != "llm_insights" and key != "llm_error":
            summary_table.add_row(key.replace("_", " ").title(), str(value))

    console.print(summary_table)

    # Temporary Practices
    if output.temporary_practices:
        console.print("\n[bold yellow]Temporary EC Practices:[/bold yellow]")
        temp_table = Table(show_header=True)
        temp_table.add_column("Practice", style="yellow")
        temp_table.add_column("Quantity", justify="right")
        temp_table.add_column("Unit")
        temp_table.add_column("Rule ID", style="dim")

        for practice in output.temporary_practices:
            temp_table.add_row(
                practice.practice_type.value,
                f"{practice.quantity:.2f}",
                practice.unit,
                practice.rule_id,
            )

        console.print(temp_table)

    # Permanent Practices
    if output.permanent_practices:
        console.print("\n[bold green]Permanent EC Practices:[/bold green]")
        perm_table = Table(show_header=True)
        perm_table.add_column("Practice", style="green")
        perm_table.add_column("Quantity", justify="right")
        perm_table.add_column("Unit")
        perm_table.add_column("Rule ID", style="dim")

        for practice in output.permanent_practices:
            perm_table.add_row(
                practice.practice_type.value,
                f"{practice.quantity:.2f}",
                practice.unit,
                practice.rule_id,
            )

        console.print(perm_table)

    # Pay Items
    if output.pay_items:
        console.print("\n[bold blue]Pay Items:[/bold blue]")
        pay_table = Table(show_header=True)
        pay_table.add_column("Item #", style="blue")
        pay_table.add_column("Description")
        pay_table.add_column("Quantity", justify="right")
        pay_table.add_column("Unit")
        pay_table.add_column("Est. Cost", justify="right")

        for item in output.pay_items:
            cost_str = (
                f"${item.estimated_unit_cost * item.quantity:.2f}"
                if item.estimated_unit_cost
                else "N/A"
            )
            pay_table.add_row(
                item.item_number,
                item.description,
                f"{item.quantity:.2f}",
                item.unit,
                cost_str,
            )

        console.print(pay_table)

    # LLM Insights
    if "llm_insights" in output.summary:
        console.print("\n[bold magenta]LLM Insights:[/bold magenta]")
        console.print(output.summary["llm_insights"])

    if "llm_error" in output.summary:
        console.print(f"\n[yellow]LLM Error: {output.summary['llm_error']}[/yellow]")


@app.command()
def process(
    input_file: Annotated[
        Path,
        typer.Argument(
            help="Path to project input file (YAML or JSON)", exists=True, dir_okay=False
        ),
    ],
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Path to save output file (YAML or JSON). If not provided, only prints to console."
            ),
        ),
    ] = None,
    rules_file: Annotated[
        Path | None,
        typer.Option(
            "--rules",
            "-r",
            help="Path to custom rules file (YAML). If not provided, uses default rules.",
            exists=True,
        ),
    ] = None,
    use_llm: Annotated[
        bool,
        typer.Option("--llm/--no-llm", help="Enable LLM-enhanced recommendations"),
    ] = False,
    llm_api_key: Annotated[
        str | None,
        typer.Option("--llm-api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)"),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress console output"),
    ] = False,
) -> None:
    """Process a project and generate EC recommendations.

    Reads project data from INPUT_FILE (YAML or JSON format), applies rules
    to determine appropriate erosion control practices and pay items, and
    outputs results.
    """
    try:
        # Load project data
        if not quiet:
            console.print(f"[cyan]Loading project from {input_file}...[/cyan]")
        project = load_project(input_file)

        # Initialize rules engine
        engine = RulesEngine(rules_path=rules_file)
        if not quiet:
            console.print(f"[cyan]Loaded {len(engine.rules)} rules[/cyan]")

        # Process project
        if not quiet:
            console.print("[cyan]Processing project...[/cyan]")
        output = engine.process_project(project)

        # Apply LLM enhancement if requested
        if use_llm:
            if not quiet:
                console.print("[cyan]Enhancing with LLM...[/cyan]")
            try:
                api_key = resolve_api_key(llm_api_key)
                if api_key:
                    adapter = OpenAIAdapter(api_key=api_key)
                else:
                    console.print(
                        "[yellow]Warning: OpenAI API key not found. "
                        "Using mock LLM adapter.[/yellow]"
                    )
                    adapter = MockLLMAdapter()
                output = adapter.enhance_recommendations(project, output)
            except ImportError:
                console.print(
                    "[yellow]Warning: OpenAI package not installed. "
                    "Using mock LLM adapter.[/yellow]"
                )
                adapter = MockLLMAdapter()
                output = adapter.enhance_recommendations(project, output)

        # Save output if path provided
        if output_file:
            save_output(output, output_file)
            if not quiet:
                console.print(f"[green]✓ Results saved to {output_file}[/green]")

        # Print summary to console
        if not quiet:
            print_summary(output)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def validate(
    input_file: Annotated[
        Path,
        typer.Argument(help="Path to project input file to validate", exists=True, dir_okay=False),
    ],
) -> None:
    """Validate a project input file.

    Checks that the file is valid YAML/JSON and conforms to the ProjectInput schema.
    """
    try:
        console.print(f"[cyan]Validating {input_file}...[/cyan]")
        project = load_project(input_file)
        console.print("[green]✓ File is valid![/green]")
        console.print(f"\nProject: {project.project_name}")
        console.print(f"Jurisdiction: {project.jurisdiction}")
        console.print(f"Total Disturbed Acres: {project.total_disturbed_acres}")
        console.print(f"Predominant Soil: {project.predominant_soil.value}")
        console.print(f"Predominant Slope: {project.predominant_slope.value}")
        console.print(f"Drainage Features: {len(project.drainage_features)}")
        console.print(f"Project Phases: {len(project.phases)}")
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        raise typer.Exit(code=1) from e


@app.command()
def version() -> None:
    """Show version information."""
    from ec_agent import __version__

    console.print(f"EC Agent version {__version__}")


if __name__ == "__main__":
    app()
