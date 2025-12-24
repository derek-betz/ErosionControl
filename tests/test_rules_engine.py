from pathlib import Path

from ec_agent.indexer import build_index
from ec_agent.retriever import load_index, retrieve
from ec_agent.rules_engine import generate_recommendations, load_rules
from ec_agent.schemas import ProjectContext


def test_clarifying_questions_missing_fields():
    ctx = ProjectContext(project_name="Test Project")
    questions = ctx.clarifying_questions()
    assert "disturbed area" in questions[0].lower()
    assert any("inlets" in q.lower() for q in questions)
    assert any("slopes" in q.lower() for q in questions)


def test_rules_engine_applies_multiple_rules():
    rules = load_rules(Path("rules/indot/practice_rules.yaml"))
    ctx = ProjectContext(
        project_name="Rural Widening",
        disturbed_area_ac=8.0,
        contains_inlets=False,
        near_water=True,
        work_in_wetlands=False,
        winter_construction=False,
        max_slope_percent=6,
        season="summer",
        temporary_required=True,
        permanent_required=True,
        traffic_maintenance="lane closures",
    )
    recs = generate_recommendations(ctx.model_dump(), rules)
    rule_ids = {r["rule_id"] for r in recs}
    assert "INDOT-R-002" in rule_ids  # perimeter control
    assert "INDOT-R-006" in rule_ids  # permanent seeding
    assert len(recs) >= 5


def test_retriever_returns_indot_citation(tmp_path):
    resources = Path("indot_resources")
    index_path = tmp_path / "index.pkl"
    build_index(resources, index_path)

    idx = load_index(index_path)
    results = retrieve("silt fence perimeter control", idx, top_k=1)
    assert results
    assert results[0].doc_id.startswith("INDOT")
