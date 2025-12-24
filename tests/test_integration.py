"""Integration tests for the complete EC Agent workflow."""

import json

import pytest
import yaml

from ec_agent.llm_adapter import MockLLMAdapter
from ec_agent.models import DrainageFeature, ProjectInput, ProjectPhase, SlopeType, SoilType
from ec_agent.rules_engine import RulesEngine


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return ProjectInput(
        project_name="Integration Test Project",
        jurisdiction="Test State DOT",
        total_disturbed_acres=4.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=18.0,
        drainage_features=[
            DrainageFeature(
                id="INLET-001",
                type="inlet",
                location="Station 10+50",
                drainage_area_acres=2.0,
            ),
            DrainageFeature(
                id="OUTFALL-001",
                type="outfall",
                location="Station 20+00",
                drainage_area_acres=3.5,
            ),
        ],
        phases=[
            ProjectPhase(
                phase_id="PHASE-1",
                name="Clearing and Grubbing",
                duration_days=10,
                disturbed_acres=4.5,
            ),
            ProjectPhase(
                phase_id="PHASE-2",
                name="Grading",
                duration_days=30,
                disturbed_acres=4.5,
            ),
        ],
        metadata={"project_engineer": "Test Engineer", "permit": "TEST-12345"},
    )


def test_complete_workflow(sample_project):
    """Test the complete workflow from input to output."""
    # Initialize engine
    engine = RulesEngine()

    # Process project
    output = engine.process_project(sample_project)

    # Verify output structure
    assert output.project_name == sample_project.project_name
    assert output.timestamp is not None
    assert len(output.temporary_practices) > 0
    assert len(output.permanent_practices) > 0
    assert len(output.pay_items) > 0

    # Verify summary
    assert output.summary["total_temporary_practices"] == len(output.temporary_practices)
    assert output.summary["total_permanent_practices"] == len(output.permanent_practices)
    assert output.summary["total_pay_items"] == len(output.pay_items)
    assert output.summary["total_estimated_cost"] > 0

    # Verify all practices have required fields
    for practice in output.temporary_practices + output.permanent_practices:
        assert practice.practice_type is not None
        assert practice.quantity > 0
        assert practice.unit is not None
        assert practice.rule_id is not None
        assert practice.rule_source is not None
        assert practice.justification is not None

    # Verify all pay items have required fields
    for item in output.pay_items:
        assert item.item_number is not None
        assert item.description is not None
        assert item.quantity > 0
        assert item.unit is not None
        assert item.rule_id is not None


def test_workflow_with_llm_enhancement(sample_project):
    """Test workflow with LLM enhancement."""
    engine = RulesEngine()
    llm_adapter = MockLLMAdapter()

    # Process without LLM
    base_output = engine.process_project(sample_project)

    # Enhance with LLM
    enhanced_output = llm_adapter.enhance_recommendations(sample_project, base_output)

    # Verify LLM insights were added
    assert "llm_insights" in enhanced_output.summary
    assert len(enhanced_output.summary["llm_insights"]) > 0

    # Verify base data is still present
    assert len(enhanced_output.temporary_practices) == len(base_output.temporary_practices)
    assert len(enhanced_output.permanent_practices) == len(base_output.permanent_practices)


def test_yaml_serialization(sample_project, tmp_path):
    """Test YAML serialization and deserialization."""
    engine = RulesEngine()
    output = engine.process_project(sample_project)

    # Save to YAML
    yaml_path = tmp_path / "output.yaml"
    output_dict = output.model_dump(mode="json")
    with open(yaml_path, "w") as f:
        yaml.safe_dump(output_dict, f)

    # Read back
    with open(yaml_path) as f:
        loaded_dict = yaml.safe_load(f)

    assert loaded_dict["project_name"] == sample_project.project_name
    assert len(loaded_dict["temporary_practices"]) > 0
    assert len(loaded_dict["pay_items"]) > 0


def test_json_serialization(sample_project, tmp_path):
    """Test JSON serialization and deserialization."""
    engine = RulesEngine()
    output = engine.process_project(sample_project)

    # Save to JSON
    json_path = tmp_path / "output.json"
    output_dict = output.model_dump(mode="json")
    with open(json_path, "w") as f:
        json.dump(output_dict, f, indent=2)

    # Read back
    with open(json_path) as f:
        loaded_dict = json.load(f)

    assert loaded_dict["project_name"] == sample_project.project_name
    assert len(loaded_dict["temporary_practices"]) > 0
    assert len(loaded_dict["pay_items"]) > 0


def test_project_input_from_yaml(tmp_path):
    """Test loading project input from YAML."""
    yaml_content = """
project_name: YAML Test Project
jurisdiction: Test County
total_disturbed_acres: 3.0
predominant_soil: sand
predominant_slope: gentle
average_slope_percent: 10.0
drainage_features: []
phases: []
metadata: {}
"""
    yaml_path = tmp_path / "input.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    # Load and validate
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    project = ProjectInput(**data)
    assert project.project_name == "YAML Test Project"
    assert project.total_disturbed_acres == 3.0
    assert project.predominant_soil == SoilType.SAND


def test_project_input_from_json(tmp_path):
    """Test loading project input from JSON."""
    json_content = {
        "project_name": "JSON Test Project",
        "jurisdiction": "Test State",
        "total_disturbed_acres": 2.5,
        "predominant_soil": "loam",
        "predominant_slope": "moderate",
        "average_slope_percent": 12.0,
        "drainage_features": [],
        "phases": [],
        "metadata": {},
    }
    json_path = tmp_path / "input.json"
    with open(json_path, "w") as f:
        json.dump(json_content, f)

    # Load and validate
    with open(json_path) as f:
        data = json.load(f)

    project = ProjectInput(**data)
    assert project.project_name == "JSON Test Project"
    assert project.total_disturbed_acres == 2.5
    assert project.predominant_soil == SoilType.LOAM


def test_traceability_of_rules(sample_project):
    """Test that all outputs have traceable rule IDs and sources."""
    engine = RulesEngine()
    output = engine.process_project(sample_project)

    # Collect all rule IDs from practices
    practice_rule_ids = {p.rule_id for p in output.temporary_practices + output.permanent_practices}

    # Collect all rule IDs from pay items
    pay_item_rule_ids = {item.rule_id for item in output.pay_items}

    # Verify all are non-empty
    assert all(rule_id for rule_id in practice_rule_ids)
    assert all(rule_id for rule_id in pay_item_rule_ids)

    # Verify practices and pay items share rule IDs (they should match)
    assert practice_rule_ids == pay_item_rule_ids

    # Verify all rule sources are present
    for practice in output.temporary_practices + output.permanent_practices:
        assert len(practice.rule_source) > 0
        assert practice.rule_source in [
            "EPA NPDES CGP",
            "Local Stormwater Ordinance",
            "State DOT Standard Specifications",
        ]


def test_cost_estimation(sample_project):
    """Test cost estimation calculations."""
    engine = RulesEngine()
    output = engine.process_project(sample_project)

    # Calculate expected total
    expected_total = sum(
        (item.estimated_unit_cost or 0) * item.quantity for item in output.pay_items
    )

    assert abs(output.summary["total_estimated_cost"] - expected_total) < 0.01

    # Verify at least some items have costs
    items_with_cost = [item for item in output.pay_items if item.estimated_unit_cost]
    assert len(items_with_cost) > 0
