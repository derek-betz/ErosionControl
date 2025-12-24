"""Tests for data models."""

import pytest
from pydantic import ValidationError

from ec_agent.models import (
    DrainageFeature,
    ECPractice,
    ECPracticeType,
    PayItem,
    ProjectInput,
    ProjectPhase,
    SlopeType,
    SoilType,
)


def test_soil_type_enum():
    """Test SoilType enum values."""
    assert SoilType.CLAY.value == "clay"
    assert SoilType.SAND.value == "sand"
    assert SoilType.LOAM.value == "loam"


def test_slope_type_enum():
    """Test SlopeType enum values."""
    assert SlopeType.FLAT.value == "flat"
    assert SlopeType.STEEP.value == "steep"
    assert SlopeType.VERY_STEEP.value == "very_steep"


def test_drainage_feature_creation():
    """Test creating a drainage feature."""
    feature = DrainageFeature(
        id="INLET-001",
        type="inlet",
        location="Station 10+50",
        drainage_area_acres=2.5,
        additional_properties={"inlet_type": "curb_inlet"},
    )
    assert feature.id == "INLET-001"
    assert feature.drainage_area_acres == 2.5
    assert feature.additional_properties["inlet_type"] == "curb_inlet"


def test_drainage_feature_validation():
    """Test drainage feature validation."""
    with pytest.raises(ValidationError):
        DrainageFeature(
            id="INLET-001",
            type="inlet",
            location="Station 10+50",
            drainage_area_acres=-1.0,  # Invalid: must be > 0
        )


def test_project_phase_creation():
    """Test creating a project phase."""
    phase = ProjectPhase(
        phase_id="PHASE-1",
        name="Grading",
        duration_days=30,
        disturbed_acres=5.0,
        description="Initial grading work",
    )
    assert phase.phase_id == "PHASE-1"
    assert phase.duration_days == 30
    assert phase.disturbed_acres == 5.0


def test_project_input_creation():
    """Test creating a complete project input."""
    project = ProjectInput(
        project_name="Test Project",
        jurisdiction="Test County",
        total_disturbed_acres=3.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )
    assert project.project_name == "Test Project"
    assert project.total_disturbed_acres == 3.5
    assert project.predominant_soil == SoilType.CLAY
    assert project.predominant_slope == SlopeType.MODERATE
    assert len(project.drainage_features) == 0  # Default empty list


def test_project_input_with_features():
    """Test project input with drainage features and phases."""
    project = ProjectInput(
        project_name="Complex Project",
        jurisdiction="State DOT",
        total_disturbed_acres=10.0,
        predominant_soil=SoilType.SAND,
        predominant_slope=SlopeType.STEEP,
        average_slope_percent=30.0,
        drainage_features=[
            DrainageFeature(
                id="INLET-1", type="inlet", location="Station 1", drainage_area_acres=2.0
            )
        ],
        phases=[ProjectPhase(phase_id="P1", name="Phase 1", duration_days=20, disturbed_acres=5.0)],
    )
    assert len(project.drainage_features) == 1
    assert len(project.phases) == 1
    assert project.drainage_features[0].id == "INLET-1"


def test_project_input_validation():
    """Test project input validation."""
    # Invalid: negative disturbed acres
    with pytest.raises(ValidationError):
        ProjectInput(
            project_name="Test",
            jurisdiction="Test",
            total_disturbed_acres=-1.0,
            predominant_soil=SoilType.CLAY,
            predominant_slope=SlopeType.FLAT,
            average_slope_percent=5.0,
        )

    # Invalid: slope percent > 100
    with pytest.raises(ValidationError):
        ProjectInput(
            project_name="Test",
            jurisdiction="Test",
            total_disturbed_acres=1.0,
            predominant_soil=SoilType.CLAY,
            predominant_slope=SlopeType.FLAT,
            average_slope_percent=150.0,
        )


def test_ec_practice_creation():
    """Test creating an EC practice."""
    practice = ECPractice(
        practice_type=ECPracticeType.SILT_FENCE,
        is_temporary=True,
        quantity=500.0,
        unit="LF",
        location="Perimeter",
        rule_id="RULE-001",
        rule_source="EPA NPDES",
        justification="Perimeter sediment control",
    )
    assert practice.practice_type == ECPracticeType.SILT_FENCE
    assert practice.is_temporary is True
    assert practice.quantity == 500.0
    assert practice.unit == "LF"


def test_pay_item_creation():
    """Test creating a pay item."""
    pay_item = PayItem(
        item_number="EC-001",
        description="Silt Fence, Type A",
        quantity=500.0,
        unit="LF",
        estimated_unit_cost=3.50,
        ec_practice_ref="silt_fence_RULE-001",
        rule_id="RULE-001",
        rule_source="EPA NPDES",
    )
    assert pay_item.item_number == "EC-001"
    assert pay_item.quantity == 500.0
    assert pay_item.estimated_unit_cost == 3.50


def test_pay_item_validation():
    """Test pay item validation."""
    # Invalid: negative quantity
    with pytest.raises(ValidationError):
        PayItem(
            item_number="EC-001",
            description="Test Item",
            quantity=-10.0,
            unit="EA",
            ec_practice_ref="test",
            rule_id="RULE-001",
            rule_source="Test",
        )

    # Invalid: negative unit cost
    with pytest.raises(ValidationError):
        PayItem(
            item_number="EC-001",
            description="Test Item",
            quantity=10.0,
            unit="EA",
            estimated_unit_cost=-5.0,
            ec_practice_ref="test",
            rule_id="RULE-001",
            rule_source="Test",
        )
