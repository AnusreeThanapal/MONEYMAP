"""
MoneyMap — FastAPI main entry point.
All routes wired up through phases 1-6.
"""
import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database import init_db, reset_db
from app.analytics import get_summary
from app.ingest import ingest_file, ingest_demo
from app.anomalies import get_anomalies_with_explanations
from app.agent import run_agent

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="MoneyMap API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    model = os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")
    print(f"MoneyMap DB initialised | Model: {model}")
    try:
        from scripts.seed_demo_cache import seed_demo_cache
        seed_demo_cache()
    except Exception as e:
        print(f"Demo cache seeding error: {e}")


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "model": os.environ.get("MONEYMAP_MODEL", "gemma4:e4b")}


# ── Reset ──────────────────────────────────────────────────────────────────────

@app.post("/api/reset")
def reset():
    reset_db()
    # Clear extraction cache and reseed demo
    cache_dir = Path(__file__).parent.parent / "extraction_cache"
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            f.unlink()
    try:
        from scripts.seed_demo_cache import seed_demo_cache
        seed_demo_cache()
    except Exception as e:
        print(f"Demo cache re-seeding error: {e}")
    return {"status": "reset"}


# ── Ingest files ───────────────────────────────────────────────────────────────

@app.post("/api/ingest")
async def ingest_files(files: list[UploadFile] = File(...)):
    results = []
    for upload in files:
        # Save temp file
        dest = UPLOAD_DIR / upload.filename
        t0   = time.time()
        content = await upload.read()
        dest.write_bytes(content)

        summary = ingest_file(dest)
        summary["elapsed_s"] = round(time.time() - t0, 1)
        results.append(summary)

    return {"results": results}


# ── Demo load ──────────────────────────────────────────────────────────────────

@app.post("/api/demo/load")
def load_demo():
    t0      = time.time()
    results = ingest_demo()
    return {
        "results":   results,
        "elapsed_s": round(time.time() - t0, 1),
    }


# ── Summary dashboard ──────────────────────────────────────────────────────────

@app.get("/api/summary")
def summary():
    return get_summary()


# ── Anomalies ──────────────────────────────────────────────────────────────────

@app.get("/api/anomalies")
def anomalies():
    return {"anomalies": get_anomalies_with_explanations()}


# ── Goals ──────────────────────────────────────────────────────────────────────

class GoalRequest(BaseModel):
    name:          str
    target_amount: float
    months:        int


@app.post("/api/goals")
def create_goal(req: GoalRequest):
    from app.database import get_db
    from app.tools import project_goal

    conn = get_db()
    cur  = conn.execute(
        "INSERT INTO goals(name, target_amount, months) VALUES(?,?,?)",
        (req.name, req.target_amount, req.months)
    )
    conn.commit()
    goal_id = cur.lastrowid
    conn.close()

    plan = project_goal(req.target_amount, req.months)

    # Ask Gemma for a 2-sentence summary with trade-off suggestions
    from app.agent import run_agent
    summary_resp = run_agent(
        f"I want to save ₹{req.target_amount:,.0f} in {req.months} months for '{req.name}'. "
        f"Based on tool results, give me 2 concrete trade-off suggestions to help reach this goal.",
        []
    )

    return {
        "id":      goal_id,
        "name":    req.name,
        "plan":    plan,
        "summary": summary_resp["answer"],
        "tool_calls": summary_resp["tool_calls"],
    }


@app.get("/api/goals")
def list_goals():
    from app.database import get_db
    conn  = get_db()
    rows  = conn.execute("SELECT * FROM goals ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"goals": [dict(r) for r in rows]}


# ── Chat ───────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/chat")
def chat(req: ChatRequest):
    t0     = time.time()
    result = run_agent(req.message, req.history)
    result["elapsed_s"] = round(time.time() - t0, 1)
    return result
