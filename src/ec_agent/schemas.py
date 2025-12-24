from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict
import yaml


class ProjectContext(BaseModel):
    """Normalized project inputs for rules evaluation."""

    model_config = ConfigDict(extra="allow")

    project_name: str
    location: Optional[str] = None
    description: Optional[str] = None
    phase: Optional[str] = None
    jurisdiction: str = "INDOT"
    temporary_required: bool = True
    permanent_required: bool = True
    disturbed_area_ac: Optional[float] = None
    contains_inlets: Optional[bool] = None
    near_water: Optional[bool] = None
    work_in_wetlands: Optional[bool] = None
    winter_construction: Optional[bool] = None
    max_slope_percent: Optional[float] = None
    soil_type: Optional[str] = None
    dominant_cover: Optional[str] = None
    season: Optional[str] = None
    rainfall_risk: Optional[str] = None
    traffic_maintenance: Optional[str] = None

    def clarifying_questions(self) -> List[str]:
        """Return missing key inputs that drive rules."""
        questions: List[str] = []
        if self.disturbed_area_ac is None:
            questions.append("What is the total disturbed area (acres)?")
        if self.contains_inlets is None:
            questions.append("Are there inlets within or downstream of the project limits?")
        if self.near_water is None:
            questions.append("Is work adjacent to waterways, wetlands, or other waters?")
        if self.max_slope_percent is None:
            questions.append("What are the maximum exposed slopes (%)?")
        if self.season is None:
            questions.append("Which construction season will major earthwork occur in?")
        return questions

    @staticmethod
    def from_yaml(path: Path | str) -> "ProjectContext":
        data = yaml.safe_load(Path(path).read_text())
        return ProjectContext(**data)

    def summary(self) -> str:
        parts = [
            f"Project: {self.project_name}",
            f"Location: {self.location or 'N/A'}",
            f"Disturbed area (ac): {self.disturbed_area_ac or 'N/A'}",
            f"Max slope (%): {self.max_slope_percent or 'N/A'}",
            f"Season: {self.season or 'N/A'}",
        ]
        return "\n".join(parts)
