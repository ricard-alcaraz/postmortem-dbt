# postmortem-to-dbt

**Turn incident postmortems into regression tests automatically.**

You know that feeling when a data incident happens, you write a detailed postmortem, fix the bug, and then... nothing prevents it from happening again? The postmortem lives in Confluence, the fix lives in code, but the *knowledge* of what went wrong never makes it into your test suite.

`postmortem-dbt` closes that gap. Paste in a plain-English incident writeup, and it generates a dbt test that would have caught it.

## ✨ What It Does

- **Reads** your incident postmortem (Markdown, plain text, whatever)
- **Parses** your dbt project's `manifest.json` to understand your actual schema
- **Generates** the appropriate dbt test:
  - **Generic tests** (`not_null`, `unique`, `accepted_values`) for simple data quality issues
  - **Singular tests** (custom SQL) for complex business logic, conditional rules, and cross-table grain issues
- **Writes** the test directly to your dbt project (`schema.yml` or `tests/*.sql`)

## 🚀 Quick Start

### Installation

```bash
pip install -e .
```
## Business Analysis

You can check my Business Analysis over this project on my personal webpage [View Analysis](https://ricard-alcaraz.com/blog/2026-09-04-bridging-the-gap-turning-incident-knowledge-into-automated-tests/)
