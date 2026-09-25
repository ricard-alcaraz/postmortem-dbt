# src/postmortem_dbt/core/validation.py
import re
import yaml
from typing import List
from .models import DbtTestProposal
from ..dbt.manifest import DbtManifest

def validate_proposal(proposal: DbtTestProposal, manifest: DbtManifest) -> List[str]:
    errors = []
    if not proposal.testable: return errors

    node = manifest.get_model_node(proposal.target_table)
    if not node:
        errors.append(f"Target table '{proposal.target_table}' not found in manifest. Available: {list(manifest.models_by_name.keys())[:5]}")
        return errors

    # NEW: Enforce target_column for known column-level tests
    col_level_tests = ['not_null', 'unique', 'accepted_values', 'relationships']
    is_col_test = any(t in proposal.test_code.lower() or t in proposal.test_name.lower() for t in col_level_tests)
    
    if is_col_test and not proposal.target_column:
        errors.append(f"Test '{proposal.test_name}' is a column-level test ({col_level_tests}) but target_column is missing. You MUST specify the exact column name.")

    # Case-insensitive column check
    if proposal.target_column:
        columns = node.get('columns', {})
        # Check exact match first
        if proposal.target_column not in columns:
            # Check case-insensitive match
            found = False
            for actual_col in columns.keys():
                if actual_col.lower() == proposal.target_column.lower():
                    proposal.target_column = actual_col # Auto-fix the casing
                    found = True
                    break
            if not found:
                errors.append(f"Target column '{proposal.target_column}' not found in '{proposal.target_table}'. Available: {list(columns.keys())}")

    if proposal.test_type == "singular":
        forbidden = re.compile(r'\b(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE)\b', re.IGNORECASE)
        if forbidden.search(proposal.test_code):
            errors.append("Singular test contains forbidden DDL/DML.")

    return errors