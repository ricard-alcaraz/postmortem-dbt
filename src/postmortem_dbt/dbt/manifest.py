# src/postmortem_dbt/dbt/manifest.py
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

class DbtManifest:
    """Parses and provides indexed access to dbt manifest.json data."""
    
    def __init__(self, manifest_path: Path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self._build_indexes()

    def _build_indexes(self):
        self.nodes_by_id: Dict[str, Any] = self.data.get('nodes', {})
        self.models_by_name: Dict[str, str] = {}
        self.tests_by_model: Dict[str, List[str]] = {}
        
        for node_id, node in self.nodes_by_id.items():
            if node.get('resource_type') == 'model':
                self.models_by_name[node.get('name')] = node_id
                self.tests_by_model[node.get('name')] = []
                
        # Index tests by exact attached_node unique_id
        for node_id, node in self.nodes_by_id.items():
            if node.get('resource_type') == 'test':
                attached_node = node.get('attached_node')
                if attached_node and attached_node in self.nodes_by_id:
                    model_name = self.nodes_by_id[attached_node].get('name')
                    if model_name:
                        self.tests_by_model[model_name].append(node.get('name', ''))

    def get_model_node(self, model_name: str) -> Optional[Dict]:
        """Returns the full raw node data for a model, or None."""
        node_id = self.models_by_name.get(model_name)
        return self.nodes_by_id.get(node_id) if node_id else None

    def get_model_schema_context(self, model_name: str) -> Optional[str]:
        """Builds a readable schema context string including raw_code."""
        node = self.get_model_node(model_name)
        if not node:
            return None
        
        lines = [f"\n### Model: {model_name}"]
        lines.append(f"Description: {node.get('description', 'None')}")
        
        columns = node.get('columns', {})
        if columns:
            lines.append("Columns:")
            for col_name, col_info in columns.items():
                lines.append(f"  - {col_name} ({col_info.get('data_type', 'unknown')}): {col_info.get('description', 'None')}")
        
        # Include raw_code for join/fanout reasoning
        raw_code = node.get('raw_code', node.get('raw_sql', ''))
        if raw_code:
            # Truncate if massive, but keep enough for join logic
            code_snippet = raw_code[:1500] + ("...\n(truncated)" if len(raw_code) > 1500 else "")
            lines.append(f"Raw Code:\n```sql\n{code_snippet}\n```")
            
        existing_tests = self.tests_by_model.get(model_name, [])
        if existing_tests:
            lines.append(f"Existing tests: {', '.join(existing_tests)}")
            
        return "\n".join(lines)

    def get_all_model_names(self) -> List[str]:
        return list(self.models_by_name.keys())