# src/postmortem_dbt/core/llm.py

import os
import json
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .models import DbtTestProposal
from ..dbt.manifest import DbtManifest

load_dotenv()

# --- Configuration ---
BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "google/gemma-4-12b") 
API_KEY = os.getenv("LLM_API_KEY", "lm-studio") 

client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
)

def _extract_json(text: str) -> dict:
    """Robustly extracts a JSON object from LLM output."""
    text = text.strip()
    
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM output:\n{text[:500]}")


def _build_schema_context(manifest: DbtManifest, model_names: list) -> str:
    """Builds a readable schema context string for the LLM."""
    if not model_names:
        return "No schema context available."
    
    context_parts = []
    for model_name in model_names:
        schema = manifest.get_model_schema(model_name)
        if schema:
            context_parts.append(f"\n### Model: {model_name}")
            context_parts.append(f"Description: {schema['description']}")
            context_parts.append("Columns:")
            for col_name, col_info in schema['columns'].items():
                context_parts.append(f"  - {col_name} ({col_info['data_type']}): {col_info['description']}")
            
            existing_tests = manifest.get_existing_tests(model_name)
            if existing_tests:
                context_parts.append(f"Existing tests: {', '.join(existing_tests)}")
    
    return "\n".join(context_parts)


def generate_dbt_test(
    incident_text: str, 
    project_path: Optional[Path] = None,
    target_models: Optional[list] = None
) -> DbtTestProposal:
    """
    Sends the incident text to the LLM with optional schema context and returns a structured DbtTestProposal.
    
    Args:
        incident_text: The plain-English incident description
        project_path: Path to the dbt project (containing target/manifest.json)
        target_models: List of model names to include in schema context (if None, includes all)
    """
    user_prompt = f"Here is the incident postmortem:\n\n{incident_text}"
    
    # Add schema context if project path is provided
    if project_path:
        manifest_path = project_path / "target" / "manifest.json"
        if manifest_path.exists():
            manifest = DbtManifest(manifest_path)
            
            # If no specific models provided, try to extract from incident or use all
            if target_models is None:
                target_models = manifest.get_all_model_names()[:5]  # Limit to first 5 to avoid token overflow
            
            schema_context = _build_schema_context(manifest, target_models)
            user_prompt += f"\n\n---\n\nSchema Context:\n{schema_context}"

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    raw_text = response.choices[0].message.content
    parsed_data = _extract_json(raw_text)

    return DbtTestProposal(**parsed_data)