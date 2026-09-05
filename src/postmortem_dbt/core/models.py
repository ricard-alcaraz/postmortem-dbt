# src/postmortem_dbt/core/models.py

from pydantic import BaseModel, Field
from typing import Optional, Literal

class DbtTestProposal(BaseModel):
    """The structured output we expect from the LLM."""
    incident_summary: str = Field(description="A 1-sentence summary of what went wrong.")
    root_cause: str = Field(description="The technical root cause of the incident.")
    target_table: str = Field(description="The primary dbt model/table that needs the test.")
    target_column: Optional[str] = Field(None, description="The specific column to test (null if table-level).")
    test_type: Literal["generic", "singular"] = Field(description="Whether it's a generic YAML test or singular SQL test.")
    test_name: str = Field(description="A descriptive name for the test (e.g., assert_no_order_fanout).")
    test_code: str = Field(description="The exact dbt YAML snippet or SQL query.")
    rationale: str = Field(description="Why this specific test catches this specific incident.")