from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .indexer import build_index
from .loader import MANIFEST_NAME, load_manifest, validate_resources
from .pay_items import load_pay_item_mapping, pay_items_for_practices
from .report import generate_report
from .retriever import load_index, retrieve
from .rules_engine import generate_recommendations, load_rules
from .schemas import ProjectContext

app = typer.Typer(help="INDOT erosion control agent")
indot_app = typer.Typer(help="INDOT resource utilities")
app.add_typer(indot_app, name="indot")


@indot_app.command("validate-resources")
def validate_resources_cmd(resources: Path = typer.Option(..., help="Path to INDOT resources")):
    errors = validate_resources(resources)
    if errors:
        for err in errors:
            typer.echo(f"ERROR: {err}")
        raise typer.Exit(code=1)
    typer.echo("Resources validated.")


@indot_app.command("build-index")
def build_index_cmd(
    resources: Path = typer.Option(..., help="Path to INDOT resources"),
    index: Path = typer.Option(..., help="Where to write the index file"),
):
    errs = validate_resources(resources)
    if errs:
        for err in errs:
            typer.echo(f"ERROR: {err}")
        raise typer.Exit(code=1)
    build_index(resources, index)
    typer.echo(f"Wrote index to {index}")


@app.command("run")
def run_cmd(
    input: Path = typer.Option(..., help="Project YAML"),
    resources: Path = typer.Option(..., help="Path to INDOT resources"),
    index: Optional[Path] = typer.Option(None, help="Prebuilt index path"),
    output: Path = typer.Option(Path("report.md"), help="Output report path"),
    no_llm: bool = typer.Option(False, help="Deterministic mode; rules-only"),
    allow_non_indot: bool = typer.Option(False, help="Allow non-INDOT citations"),
):
    context = ProjectContext.from_yaml(input)
    clarifying = context.clarifying_questions()

    errs = validate_resources(resources)
    if errs:
        for err in errs:
            typer.echo(f"ERROR: {err}")
        raise typer.Exit(code=1)
    manifest = load_manifest(resources / MANIFEST_NAME)
    manifest_doc_ids = {d["doc_id"] for d in manifest}

    # load rules and apply
    rules = load_rules(Path("rules/indot/practice_rules.yaml"))
    recs = generate_recommendations(context.model_dump(), rules)

    # derive practices
    practices = []
    for rec in recs:
        practices.extend(rec.get("recommendations", []))

    # map to pay items
    pay_map = load_pay_item_mapping(Path("rules/indot/pay_item_mapping.yaml"))
    pay_items = pay_items_for_practices(practices, pay_map)

    # attach retrieval citations if index provided
    if index and index.exists():
        idx = load_index(index)
        for rec in recs:
            query = rec.get("title") or " ".join(rec.get("recommendations", []))
            citations = retrieve(query, idx, top_k=1)
            if citations:
                doc_id = citations[0].doc_id
                if allow_non_indot or doc_id.startswith("INDOT"):
                    rec["source"] = {
                        "doc_id": doc_id,
                        "page": citations[0].page,
                        "section": citations[0].excerpt[:40],
                    }
                else:
                    rec["source"] = {"doc_id": "No INDOT citation available (placeholder)"}
            else:
                rec.setdefault("source", {"doc_id": "No INDOT citation available (placeholder)"})
    else:
        for rec in recs:
            rec.setdefault("source", {"doc_id": "No INDOT citation available (placeholder)"})

    referenced_docs = {r.get("source", {}).get("doc_id") for r in recs if r.get("source")}
    referenced_docs.update(
        item.get("source_doc_id") for item in pay_items if item.get("source_doc_id")
    )
    missing_resources = sorted(
        doc
        for doc in referenced_docs
        if doc and doc not in manifest_doc_ids and doc.startswith("INDOT")
    )

    report = generate_report(context, recs, pay_items, clarifying, missing_resources)
    output.write_text(report)
    typer.echo(f"Report written to {output}")


if __name__ == "__main__":
    app()
