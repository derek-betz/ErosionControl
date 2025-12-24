"""Tests for rules engine."""

from ec_agent.models import ProjectInput, SlopeType, SoilType
from ec_agent.rules_engine import Rule, RuleAction, RuleCondition, RulesEngine


def test_rule_condition_creation():
    """Test creating a rule condition."""
    condition = RuleCondition(field="total_disturbed_acres", operator="gt", value=1.0)
    assert condition.field == "total_disturbed_acres"
    assert condition.operator == "gt"
    assert condition.value == 1.0


def test_rule_action_creation():
    """Test creating a rule action."""
    action = RuleAction(
        practice_type="silt_fence",
        is_temporary=True,
        quantity_formula="total_disturbed_acres * 200",
        unit="LF",
        location_template="Perimeter",
        justification="Sediment control",
        pay_item_number="EC-001",
        pay_item_description="Silt Fence",
    )
    assert action.practice_type == "silt_fence"
    assert action.is_temporary is True


def test_rule_creation():
    """Test creating a complete rule."""
    rule = Rule(
        id="TEST-001",
        name="Test Rule",
        source="Test Source",
        conditions=[RuleCondition(field="total_disturbed_acres", operator="gt", value=0)],
        action=RuleAction(
            practice_type="silt_fence",
            is_temporary=True,
            quantity_formula="total_disturbed_acres * 200",
            unit="LF",
            location_template="Perimeter",
            justification="Test",
            pay_item_number="EC-001",
            pay_item_description="Test Item",
        ),
    )
    assert rule.id == "TEST-001"
    assert len(rule.conditions) == 1


def test_rules_engine_initialization():
    """Test initializing rules engine with default rules."""
    engine = RulesEngine()
    assert len(engine.rules) > 0
    # Verify rules are sorted by priority
    priorities = [rule.priority for rule in engine.rules]
    assert priorities == sorted(priorities)


def test_rules_engine_condition_evaluation():
    """Test evaluating rule conditions."""
    engine = RulesEngine()
    project = ProjectInput(
        project_name="Test",
        jurisdiction="Test",
        total_disturbed_acres=2.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )

    # Test equality
    condition_eq = RuleCondition(field="predominant_soil", operator="eq", value="clay")
    assert engine._evaluate_condition(condition_eq, project) is True

    # Test greater than
    condition_gt = RuleCondition(field="total_disturbed_acres", operator="gt", value=2.0)
    assert engine._evaluate_condition(condition_gt, project) is True

    condition_gt_false = RuleCondition(field="total_disturbed_acres", operator="gt", value=5.0)
    assert engine._evaluate_condition(condition_gt_false, project) is False

    # Test greater than or equal
    condition_gte = RuleCondition(field="total_disturbed_acres", operator="gte", value=2.5)
    assert engine._evaluate_condition(condition_gte, project) is True

    # Test less than
    condition_lt = RuleCondition(field="average_slope_percent", operator="lt", value=20.0)
    assert engine._evaluate_condition(condition_lt, project) is True

    # Test in operator
    condition_in = RuleCondition(
        field="predominant_slope", operator="in", value=["moderate", "steep"]
    )
    assert engine._evaluate_condition(condition_in, project) is True


def test_rules_engine_special_fields():
    """Test evaluation of special computed fields."""
    engine = RulesEngine()
    project = ProjectInput(
        project_name="Test",
        jurisdiction="Test",
        total_disturbed_acres=2.5,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
        drainage_features=[],
    )

    # Test has_drainage_features when empty
    condition = RuleCondition(field="has_drainage_features", operator="eq", value=False)
    assert engine._evaluate_condition(condition, project) is True


def test_rules_engine_quantity_calculation():
    """Test quantity calculation from formulas."""
    engine = RulesEngine()
    project = ProjectInput(
        project_name="Test",
        jurisdiction="Test",
        total_disturbed_acres=5.0,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )

    # Simple multiplication
    qty1 = engine._calculate_quantity("total_disturbed_acres * 200", project)
    assert qty1 == 1000.0

    # Complex formula
    qty2 = engine._calculate_quantity("total_disturbed_acres * 43560 / 9", project)
    assert abs(qty2 - 24200.0) < 0.1

    # Constant
    qty3 = engine._calculate_quantity("1", project)
    assert qty3 == 1.0


def test_rules_engine_process_project():
    """Test processing a complete project."""
    engine = RulesEngine()
    project = ProjectInput(
        project_name="Test Highway Project",
        jurisdiction="State DOT",
        total_disturbed_acres=3.0,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=15.0,
    )

    output = engine.process_project(project)

    assert output.project_name == "Test Highway Project"
    assert len(output.temporary_practices) > 0
    assert len(output.permanent_practices) > 0
    assert len(output.pay_items) > 0
    assert output.summary["total_temporary_practices"] > 0
    assert output.summary["total_permanent_practices"] > 0
    assert output.summary["total_estimated_cost"] > 0


def test_rules_engine_steep_slope_rule():
    """Test that steep slope rule is triggered correctly."""
    engine = RulesEngine()

    # Project with steep slopes
    project_steep = ProjectInput(
        project_name="Steep Project",
        jurisdiction="Test",
        total_disturbed_acres=2.0,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.STEEP,
        average_slope_percent=35.0,
    )

    output_steep = engine.process_project(project_steep)

    # Should have erosion control blanket
    blanket_practices = [
        p
        for p in output_steep.temporary_practices + output_steep.permanent_practices
        if "blanket" in p.practice_type.value
    ]
    assert len(blanket_practices) > 0

    # Project without steep slopes
    project_flat = ProjectInput(
        project_name="Flat Project",
        jurisdiction="Test",
        total_disturbed_acres=2.0,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.FLAT,
        average_slope_percent=3.0,
    )

    output_flat = engine.process_project(project_flat)

    # Should NOT have erosion control blanket
    blanket_practices_flat = [
        p
        for p in output_flat.temporary_practices + output_flat.permanent_practices
        if "blanket" in p.practice_type.value
    ]
    assert len(blanket_practices_flat) == 0


def test_rules_engine_with_drainage_features():
    """Test rules that trigger based on drainage features."""
    from ec_agent.models import DrainageFeature

    engine = RulesEngine()

    # Project with drainage features
    project = ProjectInput(
        project_name="Project with Drainage",
        jurisdiction="Test",
        total_disturbed_acres=2.0,
        predominant_soil=SoilType.CLAY,
        predominant_slope=SlopeType.MODERATE,
        average_slope_percent=10.0,
        drainage_features=[
            DrainageFeature(
                id="INLET-1", type="inlet", location="Station 1", drainage_area_acres=1.0
            ),
            DrainageFeature(
                id="INLET-2", type="inlet", location="Station 2", drainage_area_acres=1.0
            ),
        ],
    )

    output = engine.process_project(project)

    # Should have inlet protection practices
    inlet_practices = [
        p
        for p in output.temporary_practices + output.permanent_practices
        if "inlet" in p.practice_type.value
    ]
    assert len(inlet_practices) > 0
    # Quantity should match number of inlets
    assert inlet_practices[0].quantity == 2.0
