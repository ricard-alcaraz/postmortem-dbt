# src/postmortem_dbt/core/models.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List

class DbtTestProposal(BaseModel):
    """A single proposed dbt test."""
    testable: bool = Field(description="True if this incident can be prevented by a dbt test.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1.")
    incident_summary: str = Field(description="A 1-sentence summary of what went wrong.")
    root_cause: str = Field(description="The technical root cause of the incident.")
    target_table: str = Field(description="The exact dbt model name.")
    target_column: Optional[str] = Field(None, description="The specific column to test (null if table-level).")
    test_type: Literal["generic", "singular"] = Field(description="Whether it's a generic YAML test or singular SQL test.")
    test_name: str = Field(description="A descriptive snake_case name for the test.")
    test_code: str = Field(description="The exact dbt YAML snippet or SQL query.")
    rationale: str = Field(description="Why this specific test catches this specific incident.")

    @field_validator('target_column', mode='before')
    @classmethod
    def clean_target_column(cls, v):
        """Prevents the LLM from outputting 'null' as a string or empty strings."""
        if isinstance(v, str):
            v = v.strip()
            if v.lower() in ('null', 'none', '', 'n/a', 'na'):
                return None
        return v if v else None

class LLMResponse(BaseModel):
    """The root structured output we expect from the LLM."""
    proposals: List[DbtTestProposal] = Field(description="A list of proposed dbt tests.")