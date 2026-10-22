import json
import os
import time

import httpx
from dotenv import load_dotenv

from engine import MOVES

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"   # Jev, Clef (cloud)
OLLAMA_CHAT = "http://localhost:11434/api/chat"                # Qwen, Gemma (laptop)

# "id" wahi likho jo `ollama list` mein dikhe
MODELS = {
    "Jev": {"id": "typesafe/jev-1.13", "kind": "decision"},
    "Clef": {"id": "cloudflare/clef", "kind": "decision"},
    "Qwen": {"id": "qwen3:0.6b", "kind": "llm", "think": False},
    "Gemma": {"id": "gemma3:1b", "kind": "llm"},
}

TIMEOUT = 180   # sab models ke liye same
RETRIES = 1     # sab models ke liye same

_FACE = {"U": "upper", "D": "down", "L": "left", "R": "right", "F": "front", "B": "back"}


def _describe(m):
    face = _FACE[m[0]]
    if m.endswith("'"):
        return f"Turn the {face} face counterclockwise by 90 degrees"
    if m.endswith("2"):
        return f"Turn the {face} face by 180 degrees"
    return f"Turn the {face} face clockwise by 90 degrees"


CRITERIA = {m: _describe(m) for m in MOVES}
INSTRUCTIONS = ("Choose the single next move most likely to progress toward "
                "the solved cube.")
STATE_NOTE = ("cube_facelets is 54 letters in face order U R F D L B, 9 "
              "stickers per face. Solved state is UUUUUUUUURRRRRRRRRFFFFFFFFF"
              "DDDDDDDDDLLLLLLLLLBBBBBBBBB.")


class FatalAPIError(Exception):
    pass


def _post(url, payload, headers=None):
    """(data, error, latency). Same timeout + retry sab ke liye."""
    last, lat = None, 0.0
    for _ in range(RETRIES + 1):
        t0 = time.perf_counter()
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            lat = time.perf_counter() - t0
            if r.status_code in (401, 402, 403, 404):
                raise FatalAPIError(f"{r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            return r.json(), None, lat
        except FatalAPIError:
            raise
        except httpx.ConnectError:
            raise FatalAPIError("Connection nahi hua (Ollama app chal rahi hai?)")
        except Exception as e:
            lat = time.perf_counter() - t0
            last = f"{type(e).__name__}: {e}"
            time.sleep(1.5)
    return None, last, lat


def _result(move, valid, latency, error=None, conf=None, raw=None):
    return {"move": move, "valid": valid, "latency": latency,
            "error": error, "confidence": conf, "raw": raw}


# ---------- Decision models (Jev, Clef) via OpenRouter ----------
def ask_decision(model_id, state, recent):
    payload = {
        "model": model_id,
        "state": {"cube_facelets": state, "recent_moves": recent[-6:],
                  "note": STATE_NOTE},
        "questions": {
            "next_move": {
                "type": "choice",
                "instructions": INSTRUCTIONS,
                "criteria": CRITERIA,
            }
        },
    }
    headers = {"Authorization": f"Bearer {API_KEY}",
               "Content-Type": "application/json"}
    data, err, lat = _post(DECISIONS_URL, payload, headers)
    if err:
        return _result(None, False, lat, error=err)
    try:
        ans = data["answers"]["next_move"]
        move, conf = ans["choice"], ans.get("confidence")
    except Exception:
        return _result(None, False, lat, error="malformed response", raw=data)
    if move not in MOVES:
        return _result(move, False, lat, error="invalid move", conf=conf, raw=data)
    return _result(move, True, lat, conf=conf)


# ---------- LLMs (Qwen, Gemma) via Ollama ----------
SCHEMA = {
    "type": "object",
    "properties": {"move": {"type": "string", "enum": MOVES}},
    "required": ["move"],
}


def ask_llm(cfg, state, recent):
    prompt = (
        f"{INSTRUCTIONS}\n{STATE_NOTE}\n\n"
        f"cube_facelets: {state}\n"
        f"recent_moves: {recent[-6:]}\n\n"
        "Allowed moves:\n"
        + "\n".join(f"{m}: {d}" for m, d in CRITERIA.items())
        + '\n\nReply with exactly one move as JSON: {"move": "R\'"}'
    )
    payload = {
        "model": cfg["id"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "num_predict": 2000},
        "keep_alive": "10m",
    }
    if "think" in cfg:
        payload["think"] = cfg["think"]
    data, err, lat = _post(OLLAMA_CHAT, payload)
    if err:
        return _result(None, False, lat, error=err)
    try:
        move = json.loads(data["message"]["content"])["move"]
    except Exception:
        return _result(None, False, lat, error="malformed response", raw=data)
    if move not in MOVES:
        return _result(move, False, lat, error="invalid move", raw=data)
    return _result(move, True, lat)


def get_move(name, state, recent):
    cfg = MODELS[name]
    if cfg["kind"] == "decision":
        return ask_decision(cfg["id"], state, recent)
    return ask_llm(cfg, state, recent)


def warmup(name):
    """Ollama model ko RAM mein load karo, taake load ka time latency mein na judey."""
    if MODELS[name]["kind"] == "llm":
        from engine import SOLVED, apply_move
        get_move(name, apply_move(SOLVED, "R"), [])


if __name__ == "__main__":
    from engine import random_scramble
    seq, st = random_scramble(3)
    print("Scramble:", seq)
    for name in MODELS:
        warmup(name)
        print(name, "->", get_move(name, st, seq))