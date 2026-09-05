# run.py

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from postmortem_dbt.core.llm import generate_dbt_test

def main():
    parser = argparse.ArgumentParser(description="Generate dbt tests from incident postmortems")
    parser.add_argument("--incident", type=str, default="examples/incident_01.md", help="Path to incident file")
    parser.add_argument("--project", type=str, help="Path to dbt project (optional)")
    parser.add_argument("--models", type=str, nargs="*", help="Specific model names to include in context (optional)")
    
    args = parser.parse_args()
    
    incident_path = Path(args.incident)
    if not incident_path.exists():
        print(f"Error: Could not find {incident_path}")
        return

    incident_text = incident_path.read_text(encoding="utf-8")
    print(f"--- Analyzing Incident: {incident_path.name} ---\n")

    try:
        project_path = Path(args.project) if args.project else None
        proposal = generate_dbt_test(
            incident_text, 
            project_path=project_path,
            target_models=args.models
        )
        
        print(f"✅ Incident Summary: {proposal.incident_summary}")
        print(f"🔍 Root Cause: {proposal.root_cause}")
        print(f"🎯 Target: {proposal.target_table}.{proposal.target_column or '(table level)'}")
        print(f"📝 Test Type: {proposal.test_type.upper()}")
        print(f"💡 Rationale: {proposal.rationale}\n")
        
        print("--- Generated dbt Test Code ---")
        print(proposal.test_code)
        print("--------------------------------")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()