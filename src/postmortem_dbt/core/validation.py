# src/postmortem_dbt/core/validation.py
import re
import yaml
from typing import List
from .models import DbtTestProposal
from ..dbt.manifest import DbtManifest

def _is_full_model_definition(test_code: str) -> bool:
    """Detect if the LLM output a full model schema instead of just a test snippet."""
    # Check for model-level keys that shouldn't be in test_code
    model_keys = ['name:', 'description:', 'columns:', 'tests:']
    lines = test_code.strip().split('\n')
    
    # If it has multiple lines and contains model-level structure, it's wrong
    if len(lines) > 3:
        for key in model_keys:
            if any(line.strip().startswith(key) for line in lines):
                return True
    return False

def validate_proposal(proposal: DbtTestProposal, manifest: DbtManifest) -> List[str]:
    """
    Validates a single proposal against the dbt manifest and structural rules.
    Returns a list of error strings. Empty list means valid.
    """
    errors = []
    
    if not proposal.testable:
        return errors

    # 1. Check target_table exists in manifest
    node = manifest.get_model_node(proposal.target_table)
    if not node:
        errors.append(f"Target table '{proposal.target_table}' not found in manifest. Use exact names from the schema context.")
        return errors

    # 2. Check target_column exists in the model
    if proposal.target_column:
        columns = node.get('columns', {})
        if proposal.target_column not in columns:
            errors.append(f"Target column '{proposal.target_column}' not found in model '{proposal.target_table}'.")

    # 3. Check for forbidden DDL/DML in singular tests
    if proposal.test_type == "singular":
        forbidden = re.compile(r'\b(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE)\b', re.IGNORECASE)
        if forbidden.search(proposal.test_code):
            errors.append("Singular test contains forbidden DDL/DML statements. dbt tests must be SELECT queries only.")

    # 4. Validate YAML structure for generic tests
    if proposal.test_type == "generic":
        # NEW: Check if it's a full model definition
        if _is_full_model_definition(proposal.test_code):
            errors.append("test_code contains a full model schema definition. It should contain ONLY the test snippet (e.g., '- not_null' or '- unique: {severity: warn}'), not the entire model structure.")
            return errors
        
        try:
            parsed = yaml.safe_load(proposal.test_code)
            # Should be a list of tests or a single test dict
            if not isinstance(parsed, (dict, list)):
                errors.append("Generic test code did not parse into a valid YAML dictionary or list.")
            # Check it's not a model definition
            if isinstance(parsed, dict) and any(k in parsed for k in ['name', 'description', 'columns']):
                errors.append("test_code appears to be a model definition. It should be just the test (e.g., '- not_null').")
        except yaml.YAMLError as e:
            errors.append(f"Generic test code is invalid YAML: {e}")

    return errors