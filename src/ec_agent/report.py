from __future__ import annotations

from typing import Dict, List, Optional

from .citations import format_citation
from .schemas import ProjectContext


def _source_label(source: Dict | None) -> str:
    if not source:
        return "No INDOT citation available (placeholder)"
    return format_citation(source.get("doc_id", "UNKNOWN"), source.get("page"), source.get("section"))


def build_traceability(recs: List[Dict]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for rec in recs:
        for practice in rec.get("recommendations", []):
            rows.append(
                {
                    "practice": practice,
                    "rule_id": rec["rule_id"],
                    "source": _source_label(rec.get("source")),
                }
            )
    return rows


def generate_report(
    context: ProjectContext,
    recs: List[Dict],
    pay_items: List[Dict],
    clarifying_questions: List[str],
    missing_resources: Optional[List[str]] = None,
) -> str:
    temp_recs = []
    perm_recs = []
    for rec in recs:
        section = temp_recs if rec.get("phase") in ("temporary", "both", None) else perm_recs
        label = _source_label(rec.get("source"))
        for practice in rec.get("recommendations", []):
            section.append(f"- {practice} ({rec['rule_id']}): {label}")
    traceability = build_traceability(recs)

    report_lines = [
        "# INDOT Erosion Control Recommendations",
        "## Executive summary",
        "INDOT-first recommendations generated deterministically from rules and local resources.",
        "## Inputs",
        "```",
        context.summary(),
        "```",
        "## Temporary erosion control recommendations",
    ]
    report_lines.extend(temp_recs or ["- None identified"])
    report_lines.append("## Permanent erosion control recommendations")
    report_lines.extend(perm_recs or ["- None identified"])

    report_lines.append("## Pay items")
    if pay_items:
        report_lines.append("| Practice | Pay Item | Unit | Notes | Citation |")
        report_lines.append("|---|---|---|---|---|")
        for item in pay_items:
            report_lines.append(
                f"| {item['practice']} | {item['pay_item_number']} - {item['description']} "
                f"| {item.get('unit','')} | {item.get('notes','')} | "
                f"[INDOT:{item.get('source_doc_id','UNKNOWN')}] |"
            )
    else:
        report_lines.append("No pay items mapped.")

    report_lines.append("## Traceability matrix")
    report_lines.append("| Practice | Rule | INDOT source |")
    report_lines.append("|---|---|---|")
    for row in traceability:
        report_lines.append(f"| {row['practice']} | {row['rule_id']} | {row['source']} |")

    report_lines.append("## Assumptions and missing info")
    if clarifying_questions:
        report_lines.append("The following clarifications are needed:")
        report_lines.extend([f"- {q}" for q in clarifying_questions])
    else:
        report_lines.append("- All key inputs supplied.")

    report_lines.append("## Risks and notes")
    report_lines.append("- VERIFY WITH INDOT SOURCE for thresholds and pay item numbers where flagged.")

    report_lines.append("## Needs INDOT resource")
    if missing_resources:
        for doc in missing_resources:
            report_lines.append(f"- Missing INDOT resource: {doc}")
    else:
        report_lines.append("- All referenced INDOT resources present in manifest.")
    return "\n".join(report_lines)
