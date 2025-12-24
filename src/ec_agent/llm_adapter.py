"""Optional LLM adapter for enhanced EC recommendations."""

from abc import ABC, abstractmethod
from typing import Any

from ec_agent.models import ProjectInput, ProjectOutput


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""

    @abstractmethod
    def enhance_recommendations(
        self, project: ProjectInput, base_output: ProjectOutput
    ) -> ProjectOutput:
        """Enhance EC recommendations using LLM capabilities.

        Args:
            project: The project input data
            base_output: The baseline recommendations from the rules engine

        Returns:
            Enhanced ProjectOutput with LLM-generated insights
        """
        pass

    @abstractmethod
    def explain_practice(self, practice_type: str, context: dict[str, Any]) -> str:
        """Generate a detailed explanation for an EC practice.

        Args:
            practice_type: Type of EC practice
            context: Project context information

        Returns:
            Detailed explanation text
        """
        pass


class OpenAIAdapter(LLMAdapter):
    """OpenAI-based LLM adapter for EC recommendations."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4"):
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key (if None, will use OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
        """
        self.model = model
        self.api_key = api_key
        try:
            import openai

            if api_key:
                openai.api_key = api_key
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install ec-agent[llm]"
            )

    def enhance_recommendations(
        self, project: ProjectInput, base_output: ProjectOutput
    ) -> ProjectOutput:
        """Enhance EC recommendations using OpenAI.

        Args:
            project: The project input data
            base_output: The baseline recommendations from the rules engine

        Returns:
            Enhanced ProjectOutput with LLM-generated insights
        """
        # Create a prompt for the LLM
        prompt = self._create_enhancement_prompt(project, base_output)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert civil engineer specializing in erosion control "
                            "and sediment management for roadway construction projects."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower temperature for more deterministic responses
            )

            enhancement_text = response.choices[0].message.content

            # Add LLM insights to summary
            enhanced_output = base_output.model_copy(deep=True)
            enhanced_output.summary["llm_insights"] = enhancement_text

            return enhanced_output

        except Exception as e:
            # If LLM call fails, return base output with error note
            base_output.summary["llm_error"] = str(e)
            return base_output

    def explain_practice(self, practice_type: str, context: dict[str, Any]) -> str:
        """Generate a detailed explanation for an EC practice.

        Args:
            practice_type: Type of EC practice
            context: Project context information

        Returns:
            Detailed explanation text
        """
        prompt = f"""Explain the following erosion control practice in detail:
Practice: {practice_type}
Project Context: {context}

Provide:
1. Purpose and function of this practice
2. Installation requirements
3. Maintenance considerations
4. Expected effectiveness
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert civil engineer specializing in erosion control."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            return response.choices[0].message.content or "No explanation available."

        except Exception as e:
            return f"Error generating explanation: {str(e)}"

    def _create_enhancement_prompt(
        self, project: ProjectInput, base_output: ProjectOutput
    ) -> str:
        """Create a prompt for LLM enhancement.

        Args:
            project: The project input data
            base_output: The baseline recommendations

        Returns:
            Prompt string
        """
        practices_summary = "\n".join(
            [
                f"- {p.practice_type.value}: {p.quantity} {p.unit} ({p.justification})"
                for p in base_output.temporary_practices + base_output.permanent_practices
            ]
        )

        return f"""Review these erosion control recommendations for a roadway project:

Project: {project.project_name}
Jurisdiction: {project.jurisdiction}
Total Disturbed Acres: {project.total_disturbed_acres}
Predominant Soil: {project.predominant_soil.value}
Predominant Slope: {project.predominant_slope.value}
Average Slope: {project.average_slope_percent}%

Recommended Practices:
{practices_summary}

Please provide:
1. Overall assessment of the recommended practices
2. Any additional practices or considerations that should be evaluated
3. Potential risks or challenges specific to this project
4. Recommendations for sequencing or phasing of practices

Keep your response concise and actionable (under 300 words).
"""


class MockLLMAdapter(LLMAdapter):
    """Mock LLM adapter for testing without API calls."""

    def enhance_recommendations(
        self, project: ProjectInput, base_output: ProjectOutput
    ) -> ProjectOutput:
        """Mock enhancement that adds a simple message.

        Args:
            project: The project input data
            base_output: The baseline recommendations from the rules engine

        Returns:
            Enhanced ProjectOutput with mock insights
        """
        enhanced_output = base_output.model_copy(deep=True)
        enhanced_output.summary["llm_insights"] = (
            "Mock LLM Insights: The recommended practices appear appropriate for "
            f"a {project.total_disturbed_acres}-acre project with {project.predominant_slope.value} "
            "slopes. Consider implementing practices in phases to minimize cost and maximize effectiveness."
        )
        return enhanced_output

    def explain_practice(self, practice_type: str, context: dict[str, Any]) -> str:
        """Generate a mock explanation.

        Args:
            practice_type: Type of EC practice
            context: Project context information

        Returns:
            Mock explanation text
        """
        return f"Mock explanation for {practice_type}: This is a standard erosion control practice."
