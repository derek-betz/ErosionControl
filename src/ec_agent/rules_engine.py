"""YAML-based rules engine for deterministic EC practice recommendations."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from ec_agent.models import (
    ECPractice,
    ECPracticeType,
    PayItem,
    ProjectInput,
    ProjectOutput,
    SlopeType,
    SoilType,
)


class RuleCondition(BaseModel):
    """Condition that must be met for a rule to apply."""

    field: str = Field(..., description="Field name to check (e.g., 'predominant_slope')")
    operator: str = Field(
        ..., description="Comparison operator (eq, ne, gt, gte, lt, lte, in, contains)"
    )
    value: Any = Field(..., description="Value to compare against")


class RuleAction(BaseModel):
    """Action to take when rule conditions are met."""

    practice_type: str = Field(..., description="Type of EC practice to apply")
    is_temporary: bool = Field(..., description="Whether practice is temporary")
    quantity_formula: str = Field(
        ..., description="Formula to calculate quantity (e.g., 'total_disturbed_acres * 200')"
    )
    unit: str = Field(..., description="Unit of measurement")
    location_template: str = Field(..., description="Template for location description")
    justification: str = Field(..., description="Justification for this practice")
    pay_item_number: str = Field(..., description="Associated pay item number")
    pay_item_description: str = Field(..., description="Pay item description")
    estimated_unit_cost: float | None = Field(None, description="Estimated cost per unit")


class Rule(BaseModel):
    """Complete rule definition."""

    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    source: str = Field(..., description="Source document/standard (e.g., 'EPA NPDES', 'State DOT')")
    priority: int = Field(default=100, description="Priority (lower number = higher priority)")
    conditions: list[RuleCondition] = Field(..., description="Conditions that trigger this rule")
    action: RuleAction = Field(..., description="Action to perform when conditions are met")
    notes: str = Field(default="", description="Additional notes about the rule")


class RulesEngine:
    """Deterministic rules engine for EC practice recommendations."""

    def __init__(self, rules_path: Path | str | None = None):
        """Initialize the rules engine.

        Args:
            rules_path: Path to YAML file containing rules. If None, uses default rules.
        """
        self.rules: list[Rule] = []
        if rules_path:
            self.load_rules(Path(rules_path))
        else:
            self._load_default_rules()

    def load_rules(self, rules_path: Path) -> None:
        """Load rules from a YAML file.

        Args:
            rules_path: Path to YAML file containing rules
        """
        with open(rules_path) as f:
            rules_data = yaml.safe_load(f)

        self.rules = [Rule(**rule_dict) for rule_dict in rules_data.get("rules", [])]
        # Sort by priority (lower number first)
        self.rules.sort(key=lambda r: r.priority)

    def _load_default_rules(self) -> None:
        """Load default built-in rules."""
        default_rules = {
            "rules": [
                {
                    "id": "SILT_FENCE_001",
                    "name": "Silt Fence for Perimeter",
                    "source": "EPA NPDES CGP",
                    "priority": 10,
                    "conditions": [{"field": "total_disturbed_acres", "operator": "gt", "value": 0}],
                    "action": {
                        "practice_type": "silt_fence",
                        "is_temporary": True,
                        "quantity_formula": "total_disturbed_acres * 200",
                        "unit": "LF",
                        "location_template": "Perimeter of disturbed area",
                        "justification": "Perimeter sediment control per EPA NPDES requirements",
                        "pay_item_number": "EC-001",
                        "pay_item_description": "Silt Fence, Type A",
                        "estimated_unit_cost": 3.50,
                    },
                },
                {
                    "id": "INLET_PROT_001",
                    "name": "Inlet Protection",
                    "source": "Local Stormwater Ordinance",
                    "priority": 20,
                    "conditions": [{"field": "has_drainage_features", "operator": "eq", "value": True}],
                    "action": {
                        "practice_type": "inlet_protection",
                        "is_temporary": True,
                        "quantity_formula": "drainage_feature_count",
                        "unit": "EA",
                        "location_template": "At each drainage inlet",
                        "justification": "Protect drainage inlets from sediment",
                        "pay_item_number": "EC-002",
                        "pay_item_description": "Inlet Protection Device",
                        "estimated_unit_cost": 250.00,
                    },
                },
                {
                    "id": "STEEP_SLOPE_001",
                    "name": "Erosion Control Blanket for Steep Slopes",
                    "source": "State DOT Standard Specifications",
                    "priority": 30,
                    "conditions": [
                        {"field": "predominant_slope", "operator": "in", "value": ["steep", "very_steep"]}
                    ],
                    "action": {
                        "practice_type": "erosion_control_blanket",
                        "is_temporary": False,
                        "quantity_formula": "total_disturbed_acres * 43560 / 9",
                        "unit": "SY",
                        "location_template": "Steep slope areas",
                        "justification": "Erosion control blanket required for slopes > 25%",
                        "pay_item_number": "EC-005",
                        "pay_item_description": "Erosion Control Blanket, Type C",
                        "estimated_unit_cost": 2.75,
                    },
                },
                {
                    "id": "CONSTRUCTION_ENT_001",
                    "name": "Construction Entrance",
                    "source": "EPA NPDES CGP",
                    "priority": 40,
                    "conditions": [{"field": "total_disturbed_acres", "operator": "gte", "value": 1.0}],
                    "action": {
                        "practice_type": "construction_entrance",
                        "is_temporary": True,
                        "quantity_formula": "1",
                        "unit": "EA",
                        "location_template": "Primary site entrance",
                        "justification": "Stabilized construction entrance to prevent tracking",
                        "pay_item_number": "EC-003",
                        "pay_item_description": "Stabilized Construction Entrance",
                        "estimated_unit_cost": 1500.00,
                    },
                },
                {
                    "id": "PERM_SEED_001",
                    "name": "Permanent Seeding",
                    "source": "State DOT Standard Specifications",
                    "priority": 50,
                    "conditions": [{"field": "total_disturbed_acres", "operator": "gt", "value": 0}],
                    "action": {
                        "practice_type": "permanent_seeding",
                        "is_temporary": False,
                        "quantity_formula": "total_disturbed_acres",
                        "unit": "AC",
                        "location_template": "All disturbed areas",
                        "justification": "Permanent vegetation establishment for final stabilization",
                        "pay_item_number": "EC-010",
                        "pay_item_description": "Permanent Seeding Mix",
                        "estimated_unit_cost": 500.00,
                    },
                },
            ]
        }
        self.rules = [Rule(**rule_dict) for rule_dict in default_rules["rules"]]
        self.rules.sort(key=lambda r: r.priority)

    def _evaluate_condition(self, condition: RuleCondition, project: ProjectInput) -> bool:
        """Evaluate a single condition against project data.

        Args:
            condition: The condition to evaluate
            project: The project input data

        Returns:
            True if condition is met, False otherwise
        """
        # Get the field value from project
        field_parts = condition.field.split(".")
        value = project
        for part in field_parts:
            if part == "has_drainage_features":
                value = len(project.drainage_features) > 0
                break
            elif part == "drainage_feature_count":
                value = len(project.drainage_features)
                break
            else:
                value = getattr(value, part, None)
                if value is None:
                    return False

        # Apply operator
        op = condition.operator
        target = condition.value

        if op == "eq":
            return value == target
        elif op == "ne":
            return value != target
        elif op == "gt":
            return value > target
        elif op == "gte":
            return value >= target
        elif op == "lt":
            return value < target
        elif op == "lte":
            return value <= target
        elif op == "in":
            if isinstance(value, (SoilType, SlopeType)):
                return value.value in target
            return value in target
        elif op == "contains":
            return target in value
        else:
            return False

    def _evaluate_rule(self, rule: Rule, project: ProjectInput) -> bool:
        """Evaluate if all conditions of a rule are met.

        Args:
            rule: The rule to evaluate
            project: The project input data

        Returns:
            True if all conditions are met, False otherwise
        """
        return all(self._evaluate_condition(cond, project) for cond in rule.conditions)

    def _calculate_quantity(self, formula: str, project: ProjectInput) -> float:
        """Calculate quantity based on formula.

        Args:
            formula: Formula string (e.g., 'total_disturbed_acres * 200')
            project: The project input data

        Returns:
            Calculated quantity
        """
        # Simple formula evaluator - replace field names with values
        context = {
            "total_disturbed_acres": project.total_disturbed_acres,
            "drainage_feature_count": len(project.drainage_features),
            "average_slope_percent": project.average_slope_percent,
            "phase_count": len(project.phases),
        }

        try:
            # Evaluate the formula with the context
            result = eval(formula, {"__builtins__": {}}, context)
            return float(result)
        except Exception:
            # Default to 1 if formula evaluation fails
            return 1.0

    def _apply_action(
        self, action: RuleAction, rule: Rule, project: ProjectInput
    ) -> tuple[ECPractice, PayItem]:
        """Apply a rule action to generate EC practice and pay item.

        Args:
            action: The action to apply
            rule: The rule being applied
            project: The project input data

        Returns:
            Tuple of (ECPractice, PayItem)
        """
        quantity = self._calculate_quantity(action.quantity_formula, project)

        practice = ECPractice(
            practice_type=ECPracticeType(action.practice_type),
            is_temporary=action.is_temporary,
            quantity=quantity,
            unit=action.unit,
            location=action.location_template,
            rule_id=rule.id,
            rule_source=rule.source,
            justification=action.justification,
            notes=rule.notes,
        )

        pay_item = PayItem(
            item_number=action.pay_item_number,
            description=action.pay_item_description,
            quantity=quantity,
            unit=action.unit,
            estimated_unit_cost=action.estimated_unit_cost,
            ec_practice_ref=f"{action.practice_type}_{rule.id}",
            rule_id=rule.id,
            rule_source=rule.source,
        )

        return practice, pay_item

    def process_project(self, project: ProjectInput) -> ProjectOutput:
        """Process a project and generate EC recommendations.

        Args:
            project: The project input data

        Returns:
            ProjectOutput with EC practices and pay items
        """
        from datetime import datetime

        temporary_practices = []
        permanent_practices = []
        pay_items = []

        # Evaluate all rules
        for rule in self.rules:
            if self._evaluate_rule(rule, project):
                practice, pay_item = self._apply_action(rule.action, rule, project)

                if practice.is_temporary:
                    temporary_practices.append(practice)
                else:
                    permanent_practices.append(practice)

                pay_items.append(pay_item)

        # Calculate summary statistics
        total_estimated_cost = sum(
            (item.estimated_unit_cost or 0) * item.quantity for item in pay_items
        )

        summary = {
            "total_temporary_practices": len(temporary_practices),
            "total_permanent_practices": len(permanent_practices),
            "total_pay_items": len(pay_items),
            "total_estimated_cost": round(total_estimated_cost, 2),
        }

        return ProjectOutput(
            project_name=project.project_name,
            timestamp=datetime.now().isoformat(),
            temporary_practices=temporary_practices,
            permanent_practices=permanent_practices,
            pay_items=pay_items,
            summary=summary,
        )
