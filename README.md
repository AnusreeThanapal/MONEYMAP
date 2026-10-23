# 🗺️ MoneyMap

> AI-powered personal finance tracker with local LLM analysis via Ollama.

## Stack

| Layer | Tech |
|---|---|
| **AI** | Ollama + `gemma4:e4b` (local, private) |
| **Backend** | FastAPI + Uvicorn + PyMuPDF + ReportLab |
| **Frontend** | React + TypeScript + Vite + Recharts |

## Project Structure

```
moneymap/
├── backend/           # FastAPI app
│   ├── .venv/         # Python virtualenv
│   ├── main.py        # Entry point
│   └── requirements.txt
├── frontend/          # Vite + React TS
│   ├── src/
│   └── package.json
├── demo_data/         # Sample bank statements / CSVs
└── .gitignore
```

## Getting Started

### Prerequisites
- Ollama installed with `gemma4:e4b` pulled
- Python 3.12+
- Node.js 22+

### Backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

### Frontend

```powershell
cd frontend
npm run dev
```

### Ollama (must be running)

```powershell
ollama serve
# In another terminal:
ollama pull gemma4:e4b
```
