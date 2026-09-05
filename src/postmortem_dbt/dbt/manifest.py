# src/postmortem_dbt/dbt/manifest.py

import json
from pathlib import Path
from typing import Dict, List, Optional


class DbtManifest:
    """Parses and provides access to dbt manifest.json data."""
    
    def __init__(self, manifest_path: Path):
        with open(manifest_path, 'r') as f:
            self.data = json.load(f)
    
    def get_model_schema(self, model_name: str) -> Optional[Dict]:
        """
        Extracts schema information for a specific model.
        Returns a dict with columns, data types, and existing tests.
        """
        # Search through all nodes to find the model
        for node_id, node in self.data.get('nodes', {}).items():
            if node.get('name') == model_name and node.get('resource_type') == 'model':
                columns = {}
                for col_name, col_info in node.get('columns', {}).items():
                    columns[col_name] = {
                        'data_type': col_info.get('data_type', 'unknown'),
                        'description': col_info.get('description', ''),
                    }
                
                return {
                    'name': model_name,
                    'description': node.get('description', ''),
                    'columns': columns,
                }
        
        return None
    
    def get_all_model_names(self) -> List[str]:
        """Returns a list of all model names in the project."""
        return [
            node.get('name')
            for node in self.data.get('nodes', {}).values()
            if node.get('resource_type') == 'model'
        ]
    
    def get_existing_tests(self, model_name: str) -> List[str]:
        """Returns a list of existing test names for a model."""
        tests = []
        for node_id, node in self.data.get('nodes', {}).items():
            if node.get('resource_type') == 'test':
                # Check if this test is attached to our model
                attached_to = node.get('attached_node')
                if attached_to and model_name in attached_to:
                    tests.append(node.get('name', ''))
        return tests