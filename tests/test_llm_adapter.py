"""Tests for LLM adapter."""

from ec_agent.llm_adapter import MockLLMAdapter
from ec_agent.models import ProjectInput, SlopeType, SoilType
from ec_agent.rules_engine import RulesEngine


def test_mock_llm_adapter_initialization():
    """Test initializing mock LLM adapter."""
    adapter = MockLLMAdapter()
    assert adapter is not None


def test_mock_llm_enhance_recommendations():
    """Test mock LLM enhancement."""
    adapter = MockLLMAdapter()
    engine = RulesEngine()

    project = ProjectInput(
        project_name="Test Project",
        jurisdiction="Test County",
        total_disturbed_acres=2.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )

    base_output = engine.process_project(project)
    enhanced_output = adapter.enhance_recommendations(project, base_output)

    # Verify enhancement was added
    assert "llm_insights" in enhanced_output.summary
    assert "Mock LLM Insights" in enhanced_output.summary["llm_insights"]
    assert project.predominant_slope.value in enhanced_output.summary["llm_insights"]


def test_mock_llm_explain_practice():
    """Test mock LLM practice explanation."""
    adapter = MockLLMAdapter()

    explanation = adapter.explain_practice("silt_fence", {"project": "Test", "soil": "clay"})

    assert "silt_fence" in explanation
    assert "Mock explanation" in explanation


def test_mock_llm_preserves_base_output():
    """Test that LLM enhancement preserves original data."""
    adapter = MockLLMAdapter()
    engine = RulesEngine()

    project = ProjectInput(
        project_name="Test Project",
        jurisdiction="Test County",
        total_disturbed_acres=2.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )

    base_output = engine.process_project(project)
    base_temp_count = len(base_output.temporary_practices)
    base_perm_count = len(base_output.permanent_practices)

    enhanced_output = adapter.enhance_recommendations(project, base_output)

    # Verify original data is preserved
    assert len(enhanced_output.temporary_practices) == base_temp_count
    assert len(enhanced_output.permanent_practices) == base_perm_count
    assert enhanced_output.project_name == base_output.project_name
