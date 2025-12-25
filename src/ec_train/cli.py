"""CLI entrypoint for EC Train."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .bidtabs import scan_bidtabs, select_contracts
from .config import Config
from .erms import ERMSFetcher
from .excel_writer import FeatureRow, write_workbook
from .extractor import extract_content
from .session import SessionLog

app = typer.Typer(name="ec-train", add_completion=False)
console = Console()


def _load_seen(resume_file: Path | None, session: SessionLog, force_new: bool) -> set[str]:
    seen: set[str] = set()
    if resume_file and resume_file.exists():
        with resume_file.open() as f:
            for line in f:
                try:
                    data = json.loads(line)
                    contract = data.get("contract")
                    if contract:
                        seen.add(str(contract))
                except json.JSONDecodeError:
                    continue
    if not force_new:
        seen |= session.load()
    return seen


@app.command()
def run(
    count: Annotated[int, typer.Option("--count", "-n", help="Number of contracts to process")] = 3,
    output_dir: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Download/output directory")
    ] = Path("ec_train_output"),
    resume_file: Annotated[
        Path | None, typer.Option("--resume-file", help="Resume from a prior session log")
    ] = None,
    headless: Annotated[
        bool, typer.Option("--headless/--no-headless", help="Headless mode for scraping")
    ] = True,
    force_new_session: Annotated[
        bool, typer.Option("--force-new-session", help="Ignore previous sessions")
    ] = False,
    bidtabs_path: Annotated[
        Path | None, typer.Option(help="Path to BidTabs export (CSV/Excel)")
    ] = None,
) -> None:
    """Run the EC Train pipeline end-to-end."""
    cfg = Config.from_env()
    bidtabs_source = bidtabs_path or cfg.bidtabs_path
    if not bidtabs_source:
        raise typer.BadParameter(
            "BidTabs path must be provided via --bidtabs-path or EC_TRAIN_BIDTABS_PATH."
        )

    session_log = SessionLog(output_dir / "ec_train_sessions.jsonl")
    seen_contracts = _load_seen(resume_file, session_log, force_new_session)

    console.print(f"[cyan]Scanning BidTabs from {bidtabs_source}[/cyan]")
    contracts = scan_bidtabs(Path(bidtabs_source))
    selected = select_contracts(contracts, count=count, seen_contracts=seen_contracts, shuffle=True)
    if not selected:
        console.print("[yellow]No new contracts available.[/yellow]")
        raise typer.Exit(code=0)

    fetcher = ERMSFetcher(
        base_url=cfg.erms_url,
        download_dir=output_dir / "downloads",
        cookies=cfg.cookies,
        cookie_jar=cfg.cookie_jar,
        username=cfg.username,
        password=cfg.password,
        headless=headless,
    )

    feature_rows: list[FeatureRow] = []
    with Progress() as progress:
        task = progress.add_task("Processing contracts", total=len(selected))
        for contract in selected:
            folder_url = fetcher.search_contract(contract.contract)
            key_docs = {}
            if folder_url:
                docs = fetcher.list_documents(folder_url)
                downloads = fetcher.download_documents(
                    docs,
                    patterns=[
                        "erosion",
                        "control",
                        "drain",
                        "soil",
                        "205-12616",
                        "silt",
                        "sediment",
                        "temporary",
                        "permanent",
                        "vegetation",
                        "mulch",
                        "blanket",
                        "permits",
                        "pay",
                        "plan",
                    ],
                )
                for doc in downloads:
                    extract_content(doc.path)
                    key_docs[doc.name] = doc.path.as_posix()
            else:
                console.print(f"[yellow]Contract {contract.contract} not found in ERMS.[/yellow]")

            feature_rows.append(
                FeatureRow(
                    contract=contract.contract,
                    letting_date=contract.letting_date,
                    district=contract.district,
                    route=contract.route,
                    bidtabs_qty=contract.bidtabs_qty,
                    key_docs=key_docs,
                    notes="; ".join(list(key_docs.keys())),
                    source_url=folder_url or cfg.erms_url,
                )
            )
            progress.advance(task)

    workbook_path = write_workbook(feature_rows, output_dir)
    session_log.append([c.contract for c in selected])

    table = Table(title="EC Train Summary")
    table.add_column("Contract")
    table.add_column("Letting")
    table.add_column("Docs")
    for row in feature_rows:
        table.add_row(row.contract, row.letting_date or "-", str(len(row.key_docs or {})))
    console.print(table)
    console.print(f"[green]Workbook written to {workbook_path}[/green]")


if __name__ == "__main__":
    app()
