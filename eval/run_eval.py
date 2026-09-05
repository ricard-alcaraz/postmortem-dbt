# eval/run_eval.py

import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from postmortem_dbt.core.llm import generate_dbt_test

def run_evaluation():
    """Run the tool against the golden dataset and report accuracy."""
    
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path, 'r') as f:
        dataset = json.load(f)
    
    print(f"🧪 Running evaluation on {len(dataset)} incidents...\n")
    
    correct = 0
    total = len(dataset)
    
    for i, item in enumerate(dataset, 1):
        incident_path = Path(__file__).parent.parent / item["incident_file"]
        if not incident_path.exists():
            print(f"⚠️  Skipping {item['id']}: incident file not found")
            continue
        
        print(f"[{i}/{total}] Processing {item['id']}: {item['description']}...", end=" ", flush=True)
        
        incident_text = incident_path.read_text(encoding="utf-8")
        
        try:
            start_time = time.time()
            proposal = generate_dbt_test(incident_text)
            elapsed = time.time() - start_time
            
            # Check if the test type matches
            test_type_match = proposal.test_type == item["expected_test_type"]
            table_match = proposal.target_table == item["expected_target_table"]
            
            col_match = True
            if "expected_target_column" in item:
                col_match = proposal.target_column == item["expected_target_column"]
            
            is_correct = test_type_match and table_match and col_match
            
            if is_correct:
                print(f"✅ ({elapsed:.1f}s)")
                correct += 1
            else:
                print(f"❌ ({elapsed:.1f}s)")
                print(f"   Expected: type={item['expected_test_type']}, table={item['expected_target_table']}, col={item.get('expected_target_column', 'N/A')}")
                print(f"   Got:      type={proposal.test_type}, table={proposal.target_table}, col={proposal.target_column or 'N/A'}")
        
        except Exception as e:
            print(f"❌ ERROR - {e}")
    
    print(f"\n📊 Results: {correct}/{total} correct ({correct/total*100:.1f}%)")

if __name__ == "__main__":
    run_evaluation()