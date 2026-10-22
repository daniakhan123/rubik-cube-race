import json
import threading
import time
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from benchmark import run_trial, summarize
from models import MODELS

app = FastAPI()
SET = os.environ.get("PUZZLE_SET", "primary")
PUZZLES = json.load(open(f"puzzles_{SET}.json"))
STATE = {"running": False, "puzzle": None, "models": {}}


def fresh(p):
    return {n: {"state": p["state"], "status": "waiting", "moves": 0,
                "history": [], "current": None, "started": None,
                "total": None, "solved": None, "invalid": 0, "gap": None}
            for n in MODELS}


def worker(p):
    for name in MODELS:                       # ek ke baad ek, fair latency
        m = STATE["models"][name]
        m["status"], m["started"] = "thinking", time.time()

        def on_step(n, turn, r, state, m=m):
            m["state"] = state
            m["current"] = r["move"] if r["valid"] else "invalid"
            if r["valid"]:
                m["history"].append(r["move"])
            else:
                m["invalid"] += 1
            m["moves"] = len(m["history"])

        t = run_trial(name, p, on_step)
        m["total"], m["solved"], m["gap"] = t["total_time"], t["solved"], t["gap"]
        m["status"] = "solved" if t["solved"] else "ran_out"
    STATE["running"] = False


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/api/puzzles")
def puzzles():
    return [{"id": p["id"], "scramble": p["scramble"], "shortest": p["shortest"]}
            for p in PUZZLES]


@app.post("/api/start/{pid}")
def start(pid: int):
    if STATE["running"]:
        return {"ok": False}
    p = next(x for x in PUZZLES if x["id"] == pid)
    STATE["puzzle"] = {"id": p["id"], "scramble": p["scramble"],
                       "shortest": p["shortest"]}
    STATE["models"] = fresh(p)
    STATE["running"] = True
    threading.Thread(target=worker, args=(p,), daemon=True).start()
    return {"ok": True}


@app.get("/api/state")
def state():
    out = json.loads(json.dumps(STATE))
    for m in out["models"].values():
        if m["status"] == "thinking":
            m["elapsed"] = time.time() - m["started"]
        else:
            m["elapsed"] = m["total"] or 0
    return out


@app.get("/api/results")
def results():
    try:
        return json.load(open(f"results_{SET}.json"))["summary"]
    except Exception:
        return {}