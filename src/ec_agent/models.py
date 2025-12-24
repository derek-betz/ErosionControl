"""Data models for EC Agent inputs and outputs."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SoilType(str, Enum):
    """Soil classification types."""

    CLAY = "clay"
    SILT = "silt"
    SAND = "sand"
    GRAVEL = "gravel"
    LOAM = "loam"
    BEDROCK = "bedrock"


class SlopeType(str, Enum):
    """Slope steepness classifications."""

    FLAT = "flat"  # 0-5%
    GENTLE = "gentle"  # 5-15%
    MODERATE = "moderate"  # 15-25%
    STEEP = "steep"  # 25-50%
    VERY_STEEP = "very_steep"  # >50%


class DrainageFeature(BaseModel):
    """Model for drainage features (inlets, outfalls, etc.)."""

    id: str = Field(..., description="Unique identifier for the drainage feature")
    type: str = Field(..., description="Type of drainage feature (inlet, outfall, culvert, etc.)")
    location: str = Field(..., description="Location description")
    drainage_area_acres: float = Field(..., gt=0, description="Drainage area in acres")
    additional_properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional feature-specific properties"
    )


class ProjectPhase(BaseModel):
    """Model for project phasing information."""

    phase_id: str = Field(..., description="Unique phase identifier")
    name: str = Field(..., description="Phase name")
    duration_days: int = Field(..., gt=0, description="Estimated duration in days")
    disturbed_acres: float = Field(..., ge=0, description="Acres disturbed in this phase")
    description: str = Field(default="", description="Phase description")


class ProjectInput(BaseModel):
    """Input model for erosion control project data."""

    project_name: str = Field(..., description="Name of the project")
    jurisdiction: str = Field(..., description="Jurisdiction (state, county, city, etc.)")
    total_disturbed_acres: float = Field(..., gt=0, description="Total disturbed acres")

    # Terrain and soil characteristics
    predominant_soil: SoilType = Field(..., description="Predominant soil type")
    predominant_slope: SlopeType = Field(..., description="Predominant slope steepness")
    average_slope_percent: float = Field(..., ge=0, le=100, description="Average slope percentage")

    # Drainage features
    drainage_features: list[DrainageFeature] = Field(
        default_factory=list, description="List of drainage features"
    )

    # Project phasing
    phases: list[ProjectPhase] = Field(
        default_factory=list, description="Project phases (empty if no phasing)"
    )

    # Additional project metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional project-specific data"
    )


class ECPracticeType(str, Enum):
    """Types of erosion control practices."""

    # Temporary practices
    SILT_FENCE = "silt_fence"
    INLET_PROTECTION = "inlet_protection"
    SEDIMENT_TRAP = "sediment_trap"
    TEMPORARY_SEEDING = "temporary_seeding"
    MULCH = "mulch"
    EROSION_CONTROL_BLANKET = "erosion_control_blanket"
    CONSTRUCTION_ENTRANCE = "construction_entrance"
    DUST_CONTROL = "dust_control"

    # Permanent practices
    PERMANENT_SEEDING = "permanent_seeding"
    SODDING = "sodding"
    RIPRAP = "riprap"
    RETAINING_WALL = "retaining_wall"
    BIOSWALE = "bioswale"
    DETENTION_BASIN = "detention_basin"


class ECPractice(BaseModel):
    """Model for an erosion control practice."""

    practice_type: ECPracticeType = Field(..., description="Type of EC practice")
    is_temporary: bool = Field(..., description="Whether this is a temporary practice")
    quantity: float = Field(..., gt=0, description="Quantity of practice")
    unit: str = Field(..., description="Unit of measurement (LF, SY, EA, etc.)")
    location: str = Field(..., description="Location or application area")
    rule_id: str = Field(..., description="ID of the rule that triggered this practice")
    rule_source: str = Field(..., description="Source document/standard for the rule")
    justification: str = Field(..., description="Explanation of why this practice is needed")
    notes: str = Field(default="", description="Additional notes")


class PayItem(BaseModel):
    """Model for a construction pay item."""

    item_number: str = Field(..., description="Pay item number/code")
    description: str = Field(..., description="Pay item description")
    quantity: float = Field(..., gt=0, description="Quantity")
    unit: str = Field(..., description="Unit of measurement")
    estimated_unit_cost: float | None = Field(
        None, ge=0, description="Estimated unit cost (optional)"
    )
    ec_practice_ref: str = Field(
        ..., description="Reference to the EC practice that generated this pay item"
    )
    rule_id: str = Field(..., description="ID of the rule that determined this pay item")
    rule_source: str = Field(..., description="Source document/standard for the rule")


class ProjectOutput(BaseModel):
    """Output model for erosion control recommendations."""

    project_name: str = Field(..., description="Name of the project")
    timestamp: str = Field(..., description="ISO timestamp of generation")

    # EC practices
    temporary_practices: list[ECPractice] = Field(
        default_factory=list, description="Temporary EC practices"
    )
    permanent_practices: list[ECPractice] = Field(
        default_factory=list, description="Permanent EC practices"
    )

    # Pay items
    pay_items: list[PayItem] = Field(default_factory=list, description="Construction pay items")

    # Summary
    summary: dict[str, Any] = Field(
        default_factory=dict, description="Summary statistics and information"
    )
