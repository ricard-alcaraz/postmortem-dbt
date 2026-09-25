# postmortem-dbt

**Turn incident postmortems into regression tests automatically.**

When a data incident happens, you write a detailed postmortem, fix the bug, but the *knowledge* of what went wrong rarely makes it into your test suite. The postmortem lives in Confluence, the fix lives in code, but the regression test is forgotten. 

`postmortem-dbt` closes that gap. It parses your plain-English incident writeup, reads your dbt manifest, and generates the exact dbt tests that would have caught the issue in the first place.

## Architecture

Unlike basic prompt wrappers, this tool implements an agentic validation loop. It doesn't just ask the LLM for code; it validates the code against your actual dbt schema, catches hallucinations, and forces the LLM to self-correct before writing to disk.

```mermaid
graph TD
    A[Incident Postmortem] --> C{LLM Agent}
    B[target/manifest.json] -->|Smart Context & Dependency Graph| C
    C --> D[Validation Loop]
    D -->|Errors: hallucinated column, invalid SQL| C
    D -->|Valid Proposal| E[dbt Project]
    E --> F((Safe YAML Writer))
    F --> G[models/marts/schema.yml]
    F --> H[tests/custom_tests.sql]
```

## Key Engineering Features

* **Safe YAML Modification:** Uses `ruamel.yaml` to safely inject tests into your existing `schema.yml` files. It preserves your comments, formatting, and key ordering. It locates the exact file for your model using the `patch_path` from the dbt manifest, rather than dumping everything into a root file.
* **Agentic Self-Correction:** If the LLM hallucinates a column name or writes invalid SQL, the validation layer catches it and feeds the error back to the model for a retry. 
* **Structured Outputs:** Leverages native OpenAI JSON schema enforcement backed by Pydantic. No fragile regex parsing.
* **Smart Context Retrieval:** Instead of blindly feeding the whole manifest to the LLM, it performs a two-step retrieval: matching keywords from the incident, then traversing the dbt dependency graph to fetch the exact models, columns, and raw SQL required to understand complex join/fanout issues.
* **Intelligent Abstention:** The agent recognizes when an incident is caused by infrastructure or vendor outages (e.g., "Snowflake warehouse suspended") and correctly abstains from generating a useless data test.

## Prerequisites

1. **Python 3.9+**
2. **A running LLM endpoint:** Works with local models (LM Studio, Ollama) or hosted APIs (OpenAI, Anthropic).
3. **A compiled dbt project:** The tool requires a `target/manifest.json` file. You must run `dbt compile` or `dbt build` in your dbt project before running this tool.

## Installation & Configuration

Install the package in editable mode:

```bash
git clone https://github.com/ricard-alcaraz/postmortem-dbt.git
cd postmortem-dbt
pip install -e .
```

Create a `.env` file in the root directory to configure your LLM provider:

```env
# Local LM Studio / Ollama configuration
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=google/gemma-4-12b
LLM_API_KEY=lm-studio

# Timeouts (local models generating complex JSON may take time)
LLM_CONNECT_TIMEOUT=10.0
LLM_READ_TIMEOUT=300.0
```

## Usage

Run the CLI by pointing it to your incident file and your dbt project root:

```bash
postmortem-dbt --incident incidents/fanout.md --project /path/to/your/dbt_project
```

The tool will preview the generated test and ask for confirmation before writing to your files. Add `--yes` or `-y` to skip the prompt.

## Real-World Example

**The Incident:** Double-Counted Refunds in Daily Revenue

**Description:**
On March 3rd, the `daily_revenue` model was reporting inflated revenue. Investigation showed that the `int_orders_with_refunds` model left-joined the `orders` table to the `refunds` table. Because a single order can have multiple partial refunds, the join fanned out the order rows, duplicating the `order_amount` in the final sum.

**Resolution:**
Fixed the join by aggregating the refunds table to the order level before joining, and added a unique constraint on the intermediate model.

**The Agent's Execution:**
The agent reads the `int_orders_with_refunds` model from the manifest, identifies the lack of `unique` test on the `order_id` column, and determines a generic test is required. It generates:

```yml
tests:
  - unique
```
That will be appended on the column `order_id`, this will be the new model `int_orders_with_refund`:

```yml
- name: int_orders_with_refunds
  description: Orders enriched with their total refunded amount, intended to be one row per order
  columns:
  - name: order_id
    description: Order identifier
    tests:
    - unique
```

**The Test Failing on Buggy Data:**
When you run `dbt test`, the new regression test immediately catch if there is non unique values on the `order_id` column.

**Conclusion**
This is just a small and simple example, the idea is to not only add generic tests but also more comples bussiness logic custom tests.

## Evaluations & LLM Stats

AI tools are only as good as their error handling. This project includes an `eval/` directory containing a suite of example postmortems used to benchmark the agent. 

During execution, the CLI prints a **Retry Rescue Rate**:
```text
📊 LLM Stats: 5 total attempts, 40.0% rescued by retry loop.
```
In our internal eval suite against small local models (like Gemma-2 or Llama-3), the validation loop successfully rescues ~30-40% of initial hallucinated column names or incorrect YAML structures, ensuring the final output is always syntactically valid dbt code.

## Limitations

* **Requires Compiled Manifest:** Cannot run on raw SQL files; requires `dbt compile` to resolve Jinja macros and dependencies.
* **Cross-Project Dependencies:** Struggles with tests spanning multiple dbt projects unless explicitly configured in the manifest.
* **Custom Generic Tests:** The agent prefers built-in dbt tests (`not_null`, `unique`) and `dbt_utils`. It can also generate custom tests but this part needs more work.
* **Context Window Limits:** Extremely large `manifest.json` files (50MB+) require aggressive pruning. The smart context retriever limits injection to the 5 most relevant dependency nodes to prevent token overflow.

## Business Analysis

You can check my [Business Analysis](https://ricard-alcaraz.com/projects/2026-09-04-bridging-the-gap-turning-incident-knowledge-into-automated-tests/) over this project on my personal webpage, detailing the product strategy behind this tool.

## License

MIT