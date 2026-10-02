# Refund Agent (Terminal Prototype)

An autonomous AI employee that handles refund complaints end-to-end using a real browser to operate inside a shop back office. It decides to **refund**, **deny**, or **ask a human**, and verifies every result directly against shop records before marking a job done.

## 1. Features & Architecture

- **Browser Interaction**: Uses Playwright to interact with the shop back office like a human operator (login, search, inspect payments, click, type, submit).
- **Policy Enforcement**: Cites exact policy rules from `policy.md` behind every decision.
- **Safety & Guard Engine**: Intercepts high-risk actions (e.g., refunds exceeding $100) via `guards.json` before browser execution. Prompt injections inside customer emails cannot bypass guard checks.
- **Independent Verification**: `finish()` requires fresh browser verification on `verify_url`, plus automated database checks (`tests/test_db.py`) inspecting SQLite directly.
- **Generalization**: Task logic is general and data-driven; running a non-refund task (e.g. shipping address update) requires new files (`tasks/address_change/policy.md`), not new code.

## 2. Directory Structure

```
.
├── agent/
│   ├── browser.py       # Playwright wrapper (DOM text renderer with numbered elements)
│   ├── checker.py       # Independent verification checker
│   ├── guard.py         # Safety guard engine reading guards.json
│   ├── loop.py          # Look-Think-Do-Observe autonomous agent loop
│   ├── notes.py         # Disk-persisted structured case notes
│   ├── tools.py         # Standardized tool implementations
│   └── prompts/
│       └── system.md    # System prompt enforcing policy citation and safety rules
├── shop/
│   ├── app.py           # Flask shop back office website
│   ├── db.py            # SQLite database connection & schema
│   └── reset_db.py      # Seed data reset script
├── complaints/          # Complaint test emails (01 to 10)
├── tasks/
│   └── address_change/  # Generalization task files
├── tests/
│   └── test_db.py       # Database-level test suite
├── policy.md            # Main refund policy
├── guards.json          # Hardened safety guard configuration
├── run.py               # Main CLI runner
└── README.md
```

## 3. Quick Start

### Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Set your Gemini API Key in `.env`:
```env
GEMINI_API_KEY=your_google_gemini_api_key
```

### Running Test Cases

Initialize clean demo database and execute a complaint case:

```bash
# Case 1: Standard broken item ($60)
python run.py complaints/01_broken_item.txt --reset-db

# Case 3: Refund over $100 (triggers human approval)
python run.py complaints/03_over_100.txt

# Case 9: Prompt injection attempt
python run.py complaints/09_prompt_injection.txt
```

### Running Generalization Task

```bash
python run.py tasks/address_change/complaints/01_change_address.txt --policy tasks/address_change/policy.md
```

### Running Database Verification Suite

```bash
pytest tests/test_db.py
```

## 4. Why I Built It This Way

1. **No Refund-Specific LLM Tools**: Rather than giving the LLM a shortcut `issue_refund()` tool, the agent operates purely through standard browser actions (`browser_click`, `browser_type`, `browser_read`). This enforces real end-to-end browser automation and prevents cheating.
2. **Guards Out-of-Band**: Model-level safety prompts can fail under sophisticated prompt injections. Enforcing rules in code (`guards.json`) guarantees that critical thresholds (like refunds > $100) are hard-blocked regardless of model reasoning.
3. **Double Verification**: The agent cannot simply claim "done". The `checker.py` module inspects the actual web page on a fresh browser context, while `tests/test_db.py` asserts real SQLite state changes.
