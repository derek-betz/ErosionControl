from ec_agent.report import generate_report
from ec_agent.schemas import ProjectContext


def test_report_includes_missing_resources_section():
    ctx = ProjectContext(project_name="Test", disturbed_area_ac=1.0)
    report = generate_report(
        ctx,
        recs=[],
        pay_items=[],
        clarifying_questions=["Question?"],
        missing_resources=["INDOT-MISSING-DOC"],
    )
    assert "Needs INDOT resource" in report
    assert "INDOT-MISSING-DOC" in report
