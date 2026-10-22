import argparse
import os
import json
import statistics as st
import time
from concurrent.futures import ThreadPoolExecutor
from models import MODELS, get_move, FatalAPIError, warmup

from engine import (MOVES, apply_move, is_solved, random_scramble,
                    shortest_distance)
from models import MODELS, get_move

MAX_MOVES = 30


# ---------- Puzzles (ek baar bano, sab models ke liye same) ----------
def make_puzzles(n, lo=4, hi=5):
    puzzles = []
    for i in range(n):
        length = lo if i % 2 == 0 else hi
        seq, state = random_scramble(length)
        puzzles.append({
            "id": i + 1,
            "scramble": seq,
            "state": state,
            "shortest": shortest_distance(state),
        })
    return puzzles


# ---------- Ek model, ek puzzle ----------
def run_trial(name, puzzle, on_step=None):
    state = puzzle["state"]
    history, latencies, invalid = [], [], 0
    turns = 0
    t0 = time.perf_counter()

    while turns < MAX_MOVES and not is_solved(state):
        turns += 1
        r = get_move(name, state, history)
        latencies.append(r["latency"])
        if r["valid"]:
            state = apply_move(state, r["move"])
            history.append(r["move"])
        else:
            invalid += 1  # invalid output ek turn kha jata hai, cube nahi badalta
        if on_step:
            on_step(name, turns, r, state)

    total = time.perf_counter() - t0
    solved = is_solved(state)
    return {
        "model": name,
        "puzzle": puzzle["id"],
        "solved": solved,
        "moves": len(history),
        "turns": turns,
        "invalid": invalid,
        "shortest": puzzle["shortest"],
        "gap": (len(history) - puzzle["shortest"]) if solved else None,
        "total_time": total,
        "avg_latency": sum(latencies) / len(latencies) if latencies else None,
        "history": history,
    }


# ---------- Summary ----------
def summarize(trials):
    out = {}
    for name in MODELS:
        t = [x for x in trials if x["model"] == name]
        if not t:
            continue
        solved = [x for x in t if x["solved"]]
        gaps = [x["gap"] for x in solved]
        out[name] = {
            "trials": len(t),
            "success_rate": 100 * len(solved) / len(t),
            "avg_latency_per_move": st.mean(x["avg_latency"] for x in t if x["avg_latency"]),
            "avg_total_time": st.mean(x["total_time"] for x in t),
            "avg_moves_all": st.mean(x["moves"] for x in t),
            "avg_moves_solved": st.mean(x["moves"] for x in solved) if solved else None,
            "avg_gap_solved": st.mean(gaps) if gaps else None,
            "optimal_solves": sum(1 for g in gaps if g == 0),
            "invalid_total": sum(x["invalid"] for x in t),
        }
    return out


def print_table(s):
    f = lambda v, p=2: "-" if v is None else f"{v:.{p}f}"
    print(f"\n{'Model':<12}{'Solve%':>8}{'Lat/move':>10}{'TotalT':>9}"
          f"{'Moves':>8}{'Gap':>7}{'Optimal':>9}{'Invalid':>9}")
    for n, v in s.items():
        print(f"{n:<12}{f(v['success_rate'],0):>8}{f(v['avg_latency_per_move']):>10}"
              f"{f(v['avg_total_time'],1):>9}{f(v['avg_moves_all'],1):>8}"
              f"{f(v['avg_gap_solved']):>7}{v['optimal_solves']:>9}{v['invalid_total']:>9}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["warmup", "primary"], default="primary")
    ap.add_argument("--new", action="store_true", help="naye puzzles banao")
    ap.add_argument("--models", default="", help="jaise Jev,Clef (khaali = sab)")
    args = ap.parse_args()

    lo, hi = (3, 4) if args.set == "warmup" else (4, 5)
    pfile = f"puzzles_{args.set}.json"
    rfile = f"results_{args.set}.json"

    if args.new or not os.path.exists(pfile):
        puzzles = make_puzzles(5, lo, hi)
        json.dump(puzzles, open(pfile, "w"), indent=2)
    else:
        puzzles = json.load(open(pfile))

    names = [n for n in MODELS if not args.models or n in args.models.split(",")]

    def log(name, turn, r, state):
        print(f"  turn {turn:>2}: {r['move']} ({r['latency']:.1f}s)"
              f"{'' if r['valid'] else ' INVALID ' + str(r['error'])[:120]}")

    trials = []
    for name in names:                       # ek waqt mein ek hi model
        print(f"\n===== {name} ({args.set}) =====")
        warmup(name)
        for p in puzzles:
            print(f"Puzzle {p['id']}: scramble={p['scramble']} shortest={p['shortest']}")
            t = run_trial(name, p, log)
            trials.append(t)
            print(f"==> solved={t['solved']} moves={t['moves']} "
                  f"time={t['total_time']:.1f}s gap={t['gap']}")
            json.dump({"trials": trials, "summary": summarize(trials)},
                      open(rfile, "w"), indent=2)

    print_table(summarize(trials))
    print(f"\nSaved: {rfile}")
    