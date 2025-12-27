"""CLI entrypoint for EC Train."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from .bidtabs import BidTabContract, scan_bidtabs, select_contracts
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


def _append_unique(
    target: list[str],
    seen: set[str],
    items: list[str],
    limit: int | None = None,
) -> None:
    for item in items:
        if item in seen:
            continue
        target.append(item)
        seen.add(item)
        if limit is not None and len(target) >= limit:
            return


@app.command()
def run(
    count: Annotated[int, typer.Option("--count", "-n", help="Number of contracts to process")] = 3,
    output_dir: Annotated[
        Path | None, typer.Option("--output-dir", "-o", help="Download/output directory")
    ] = None,
    resume_file: Annotated[
        Path | None, typer.Option("--resume-file", help="Resume from a prior session log")
    ] = None,
    headless: Annotated[
        bool, typer.Option("--headless/--no-headless", help="Headless mode for scraping")
    ] = True,
    force_new_session: Annotated[
        bool, typer.Option("--force-new-session", help="Ignore previous sessions")
    ] = False,
    min_job_size: Annotated[
        float | None,
        typer.Option("--min-job-size", help="Minimum contract amount (inclusive)"),
    ] = None,
    max_job_size: Annotated[
        float | None,
        typer.Option("--max-job-size", help="Maximum contract amount (inclusive)"),
    ] = None,
    bidtabs_path: Annotated[
        Path | None, typer.Option(help="Path to BidTabs export (CSV/Excel)")
    ] = None,
    extract: Annotated[
        bool,
        typer.Option("--extract/--no-extract", help="Enable content extraction"),
    ] = True,
) -> None:
    """Run the EC Train pipeline end-to-end."""
    cfg = Config.from_env()
    output_dir = output_dir or cfg.download_dir
    bidtabs_source = bidtabs_path or cfg.bidtabs_path
    if not bidtabs_source:
        raise typer.BadParameter(
            "BidTabs path must be provided via --bidtabs-path or EC_TRAIN_BIDTABS_PATH."
        )

    session_log = SessionLog(output_dir / "ec_train_sessions.jsonl")
    seen_contracts = _load_seen(resume_file, session_log, force_new_session)

    console.print(f"[cyan]Scanning BidTabs from {bidtabs_source}[/cyan]")
    contracts = scan_bidtabs(Path(bidtabs_source))
    candidates = select_contracts(
        contracts,
        count=len(contracts),
        seen_contracts=seen_contracts,
        min_job_size=min_job_size,
        max_job_size=max_job_size,
        shuffle=True,
    )
    if not candidates:
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
    selected: list[BidTabContract] = []
    with Progress() as progress:
        task = progress.add_task("Processing contracts", total=count)
        for contract in candidates:
            if len(selected) >= count:
                break
            folder_url = fetcher.search_contract(contract.contract)
            key_docs = {}
            extracted_findings: list[str] = []
            extracted_refs: list[str] = []
            findings_seen: set[str] = set()
            refs_seen: set[str] = set()
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
                    if extract:
                        extracted = extract_content(doc.path)
                        _append_unique(extracted_refs, refs_seen, extracted.spec_refs)
                        doc_findings = [f"{doc.name}: {finding}" for finding in extracted.findings]
                        _append_unique(extracted_findings, findings_seen, doc_findings, limit=40)
                    key_docs[doc.name] = doc.path.as_posix()
                if not key_docs:
                    console.print(
                        f"[yellow]Contract {contract.contract} has no matching ERMS docs.[/yellow]"
                    )
                    continue
            else:
                console.print(f"[yellow]Contract {contract.contract} not found in ERMS.[/yellow]")
                continue

            spec_refs_text = "; ".join(extracted_refs) if extracted_refs else None
            notes_parts: list[str] = []
            if key_docs:
                notes_parts.append(f"Docs: {'; '.join(list(key_docs.keys()))}")
            if extracted_findings:
                notes_parts.append(f"Findings: {' | '.join(extracted_findings)}")
            notes_text = " | ".join(notes_parts) if notes_parts else None

            feature_rows.append(
                FeatureRow(
                    contract=contract.contract,
                    letting_date=contract.letting_date,
                    district=contract.district,
                    route=contract.route,
                    bidtabs_qty=contract.bidtabs_qty,
                    key_docs=key_docs,
                    spec_refs=spec_refs_text,
                    notes=notes_text,
                    source_url=folder_url or cfg.erms_url,
                )
            )
            selected.append(contract)
            progress.advance(task)

    if len(selected) < count:
        console.print(
            f"[yellow]Only {len(selected)} contracts had matching ERMS docs for processing."
            "[/yellow]"
        )

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
