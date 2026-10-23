# MoneyMap — Project Context

## Hackathon Problem
"From Disconnected Financial Data to Personalized Financial Well-Being"

People's money is scattered across banks, UPI wallets, credit cards, loans, investments and insurance.
MoneyMap lets users drop in screenshots and PDFs. A locally running Gemma 4 model reads them, data is
stored in SQLite, shown on a unified dashboard, and an advisor chat uses Gemma 4 native function calling.

## HARD RULES (never break these)
1. All AI runs locally via `ollama` Python client. NO cloud LLM, NO API keys. Model from env var `MONEYMAP_MODEL`, default `gemma4:e4b`.
2. LLM NEVER does arithmetic. Python tools compute every number. LLM only extracts data, selects tools, categorises merchants and explains in words.
3. Currency is INR. Format: ₹ with Indian digit grouping (e.g. ₹2,45,000).
4. Everything must work offline. No external network calls anywhere.
5. Keep code simple and readable. No over-engineering.
6. At end of every phase: run tests/commands, show real output, fix failures, only then continue.

## Repo Layout
```
/backend/app/        # FastAPI app modules
/backend/tests/      # pytest tests
/backend/scripts/    # helper scripts
/demo_data/          # synthetic files + ground_truth.json
/frontend/           # Vite + React + TS + Recharts
README.md
run.sh / run.bat
```

## Environment
- Python venv: d:\MONEYMAP\backend\.venv\Scripts\python.exe
- pip:         d:\MONEYMAP\backend\.venv\Scripts\pip.exe
- Node/npm:    C:\Program Files\nodejs\
- Ollama:      %LOCALAPPDATA%\Programs\Ollama\ollama.exe (model: gemma4:e4b)
- Backend URL: http://localhost:8000
- Frontend URL: http://localhost:5173

## Database: SQLite at backend/moneymap.db
Tables:
- accounts(id, name, type, balance, source)
- transactions(id, account_id, date, merchant, amount, direction, category, confidence, source_file, needs_review)
- goals(id, name, target_amount, months, created_at)
- anomaly_explanations(key, text)

## Fixed Category List
Food, Groceries, Transport, Shopping, Bills, Rent, Entertainment, Health, EMI, Salary, Transfers, Other

## Account Types
bank | wallet | card | loan | investment | insurance

## Anomaly Seeded in Demo Data (3)
1. Duplicate charge (same merchant, amount, date twice)
2. Unusually large transaction (mean + 3 std dev)
3. Transaction at ~3 AM

## Target Net Worth: ~Rs 2,45,000
