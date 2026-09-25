# src/postmortem_dbt/core/llm.py
import re
import logging
from pathlib import Path
from typing import Optional, List
from rich.console import Console

from .client import LLMClient
from .prompts import SYSTEM_PROMPT
from .models import LLMResponse, DbtTestProposal
from .validation import validate_proposal
from ..dbt.manifest import DbtManifest

console = Console()
logger = logging.getLogger(__name__)

# Simple in-memory tracker for retry stats
_retry_stats = {"attempts": 0, "rescued_by_retry": 0}

def _find_relevant_models(incident_text: str, manifest: DbtManifest, limit: int = 5) -> List[str]:
    """Smart retrieval: match keywords, then expand to parents/children."""
    incident_words = set(re.findall(r'\b\w+\b', incident_text.lower()))
    relevant_models = []
    
    for model_name in manifest.models_by_name.keys():
        if model_name.lower() in incident_words or model_name.lower().replace('_', ' ') in incident_text.lower():
            relevant_models.append(model_name)
            
    expanded = set(relevant_models)
    for model_name in relevant_models:
        node = manifest.get_model_node(model_name)
        if not node: continue
        
        for dep_id in node.get('depends_on', {}).get('nodes', []):
            dep_node = manifest.nodes_by_id.get(dep_id)
            if dep_node and dep_node.get('resource_type') == 'model':
                expanded.add(dep_node.get('name'))
                
    return list(expanded)[:limit]

def generate_dbt_tests(
    incident_text: str, 
    project_path: Optional[Path] = None,
    target_models: Optional[List[str]] = None,
    max_retries: int = 2
) -> List[DbtTestProposal]:
    client_wrapper = LLMClient()
    client = client_wrapper.get_client()
    model_name = client_wrapper.get_model()

    user_prompt = f"Here is the incident postmortem:\n\n{incident_text}"
    
    manifest = None
    if project_path:
        manifest_path = project_path / "target" / "manifest.json"
        if manifest_path.exists():
            manifest = DbtManifest(manifest_path)
            models_to_context = target_models or _find_relevant_models(incident_text, manifest)
            
            context_parts = []
            for m_name in models_to_context:
                schema_ctx = manifest.get_model_schema_context(m_name)
                if schema_ctx:
                    context_parts.append(schema_ctx)
            
            if context_parts:
                user_prompt += f"\n\n---\n\nRelevant dbt Schema & Code Context:\n" + "\n".join(context_parts)

    # Prepare JSON Schema for response_format
    json_schema = LLMResponse.model_json_schema()
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "dbt_test_proposals",
            "strict": False,  # False ensures compatibility with LM Studio/Ollama
            "schema": json_schema
        }
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    current_proposals = []
    errors = []
    
    for attempt in range(max_retries + 1):
        _retry_stats["attempts"] += 1
        
        if attempt > 0:
            # Exponential backoff: 2s, 4s, 8s...
            import time
            backoff_time = 2 ** attempt
            console.print(f"[yellow]⏳ Waiting {backoff_time}s before retry...[/yellow]")
            time.sleep(backoff_time)
            
            error_msg = "\n".join([f"- {e}" for e in errors])
            messages.append({"role": "user", "content": f"Your previous output had validation errors:\n{error_msg}\n\nPlease fix them and output the corrected JSON."})
            console.print(f"[yellow]🔄 Retry {attempt}/{max_retries} due to validation errors...[/yellow]")

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                response_format=response_format,
                temperature=0.2,
            )
            raw_text = response.choices[0].message.content
            parsed_data = LLMResponse.model_validate_json(raw_text)
            current_proposals = parsed_data.proposals
            
        except Exception as e:
            error_str = str(e)
            if "Connection" in error_str or "timeout" in error_str.lower():
                errors = [f"LLM connection/timeout error: {error_str}. Try increasing LLM_READ_TIMEOUT in your .env file."]
            else:
                errors = [f"Failed to parse LLM output: {error_str}"]
            console.print(f"[red]⚠️  Attempt {attempt + 1} failed: {errors[0]}[/red]")
            continue

        # Validate against manifest
        validation_errors = []
        for proposal in current_proposals:
            if proposal.testable and manifest:
                validation_errors.extend(validate_proposal(proposal, manifest))
        
        if not validation_errors:
            if attempt > 0:
                _retry_stats["rescued_by_retry"] += 1
            break  # Success!
        else:
            errors = validation_errors

    if errors and not current_proposals:
        raise ValueError(f"Failed to generate valid tests after {max_retries} retries. Last errors: {errors}")

    return current_proposals

def get_retry_stats() -> dict:
    return _retry_stats