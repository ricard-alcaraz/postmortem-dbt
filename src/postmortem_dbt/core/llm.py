# src/postmortem_dbt/core/llm.py
import os
import re
import json
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv
from openai import OpenAI

from .prompts import SYSTEM_PROMPT
from .models import DbtTestProposal
from ..dbt.manifest import DbtManifest

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "google/gemma-4-12b") 
API_KEY = os.getenv("LLM_API_KEY", "lm-studio") 

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        try: return json.loads(text)
        except json.JSONDecodeError: pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try: return json.loads(match.group())
        except json.JSONDecodeError: pass
    raise ValueError(f"Could not extract valid JSON from LLM output:\n{text[:500]}")

def _find_relevant_models(incident_text: str, manifest: DbtManifest, limit: int = 5) -> List[str]:
    """Smart retrieval: match keywords, then expand to parents/children."""
    incident_words = set(re.findall(r'\b\w+\b', incident_text.lower()))
    relevant_models = []
    
    # 1. Direct name matches
    for model_name in manifest.models_by_name.keys():
        if model_name.lower() in incident_words or model_name.lower().replace('_', ' ') in incident_text.lower():
            relevant_models.append(model_name)
            
    # 2. Expand to dependencies (parents) and dependents (children)
    expanded = set(relevant_models)
    for model_name in relevant_models:
        node = manifest.get_model_node(model_name)
        if not node: continue
        
        # Add parents
        for dep_id in node.get('depends_on', {}).get('nodes', []):
            dep_node = manifest.nodes_by_id.get(dep_id)
            if dep_node and dep_node.get('resource_type') == 'model':
                expanded.add(dep_node.get('name'))
                
    # Return unique, limited list
    return list(expanded)[:limit]

def generate_dbt_test(
    incident_text: str, 
    project_path: Optional[Path] = None,
    target_models: Optional[List[str]] = None
) -> DbtTestProposal:
    user_prompt = f"Here is the incident postmortem:\n\n{incident_text}"
    
    if project_path:
        manifest_path = project_path / "target" / "manifest.json"
        if manifest_path.exists():
            manifest = DbtManifest(manifest_path)
            
            models_to_context = target_models or _find_relevant_models(incident_text, manifest)
            
            context_parts = []
            for model_name in models_to_context:
                schema_ctx = manifest.get_model_schema_context(model_name)
                if schema_ctx:
                    context_parts.append(schema_ctx)
            
            if context_parts:
                user_prompt += f"\n\n---\n\nRelevant dbt Schema & Code Context:\n" + "\n".join(context_parts)

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