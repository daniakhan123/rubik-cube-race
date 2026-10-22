import json
import os

NAME = "Dania Khan"
ROLL = "23k-0072"          
REPO = "https://github.com/daniakhan123/rubik-cube-race"
VIDEO = "demo.mp4"        


def f(v, d=2):
    return "-" if v is None else f"{v:.{d}f}"


def load(p):
    return json.load(open(p)) if os.path.exists(p) else None


def summary_table(res):
    rows = ["| Model | Solve rate | Avg latency/move (s) | Avg total time (s) | Avg moves | Avg optimal gap (solved) | Optimal solves | Invalid |",
            "|---|---|---|---|---|---|---|---|"]
    for n, v in res["summary"].items():
        rows.append(f"| {n} | {f(v['success_rate'], 0)}% | {f(v['avg_latency_per_move'])} | "
                    f"{f(v['avg_total_time'], 1)} | {f(v['avg_moves_all'], 1)} | "
                    f"{f(v['avg_gap_solved'])} | {v['optimal_solves']} | {v['invalid_total']} |")
    return "\n".join(rows)


def trials_table(res):
    rows = ["| Model | Puzzle | Shortest | Solved | Moves | Gap | Time (s) | Invalid |",
            "|---|---|---|---|---|---|---|---|"]
    for t in res["trials"]:
        gap = "-" if t["gap"] is None else t["gap"]
        rows.append(f"| {t['model']} | {t['puzzle']} | {t['shortest']} | "
                    f"{'yes' if t['solved'] else 'no'} | {t['moves']} | {gap} | "
                    f"{t['total_time']:.1f} | {t['invalid']} |")
    return "\n".join(rows)


def answers(res):
    s = res["summary"]
    fastest = min(s, key=lambda n: s[n]["avg_latency_per_move"])
    best_sr = max(v["success_rate"] for v in s.values())
    top = [n for n, v in s.items() if v["success_rate"] == best_sr]
    solvers = {n: v for n, v in s.items() if v["avg_gap_solved"] is not None}
    rank = sorted(s, key=lambda n: (-s[n]["success_rate"],
                                    s[n]["avg_gap_solved"] if s[n]["avg_gap_solved"] is not None else 99))
    best = rank[0]

    a1 = (f"**{fastest}** was the fastest decision-maker at {s[fastest]['avg_latency_per_move']:.2f} s per move "
          f"(average over all moves and puzzles). Note: Jev, Clef (OpenRouter, cloud) and Gemma, Qwen (Ollama, "
          f"local CPU/GPU of an 8 GB laptop) run on different infrastructure, so latency reflects both the model and where it runs.")

    if best_sr == 0:
        a2 = "No model solved any primary puzzle within 30 moves (solve rate 0% for all models)."
    else:
        a2 = f"**{', '.join(top)}** achieved the highest solve rate ({best_sr:.0f}%)."

    if solvers:
        bn = min(solvers, key=lambda n: solvers[n]["avg_gap_solved"])
        a3 = (f"**{bn}** found the shortest solutions among models that solved puzzles: average optimality gap "
              f"{solvers[bn]['avg_gap_solved']:.2f} moves, with {solvers[bn]['optimal_solves']} solve(s) at exactly the "
              f"optimal length. Gaps for the others are in the table above.")
    else:
        a3 = ("Since no model solved a puzzle, an optimality gap cannot be computed for any model "
              "(gap = model moves - exact shortest moves, defined only for solved puzzles). The exact shortest "
              "distances (BFS) are listed per puzzle in the trial table.")

    if best_sr == 0:
        a4 = (f"No. The fastest model ({fastest}) did not solve more puzzles than the others: nobody solved any, "
              f"so speed did not translate into better solution quality.")
    elif fastest == best:
        a4 = f"Yes. {fastest} was both the fastest and the best on solve rate / optimality gap in this run."
    else:
        a4 = (f"No. {fastest} was fastest, but {best} had the best solution quality "
              f"(solve rate {s[best]['success_rate']:.0f}%).")

    a5 = ("I would use a **hybrid agent**: a fast decision model for cheap, low-latency routing and classification steps, "
          "and a stronger reasoning model (or a dedicated solver) when multi-step planning is needed. "
          f"Evidence from this run: the fastest model ({fastest}, {s[fastest]['avg_latency_per_move']:.2f} s/move) "
          f"reached a solve rate of {s[fastest]['success_rate']:.0f}%, and the best-performing model was {best} "
          f"({s[best]['success_rate']:.0f}%). Speed alone did not guarantee solution quality, which supports "
          "using each kind of model where it is strong.")
    return a1, a2, a3, a4, a5


prim = load("results_primary.json")
warm = load("results_warmup.json")
a1, a2, a3, a4, a5 = answers(prim)

L = []
L.append("# Rubik's Cube Race: Fast Decision Models vs Frontier-style LLMs\n")
L.append(f"**Student:** {NAME} | **Roll No:** {ROLL} | **Course:** AI Engineering, Assignment 02\n")
L.append(f"**Repository:** {REPO}\n")
L.append(f"## Demo video\n\n[Watch the screen recording]({VIDEO})  (file `{VIDEO}` in this repo)\n")
L.append("The recording shows the in-progress stage, the completion stage, and the final statistics. "
         "Name and roll number are visible on screen throughout.\n")
L.append("## What this project does\n\nFour models play the same scrambled 3x3 Rubik's Cube. Each turn the model receives "
         "the cube state (54-character facelet string) and recent moves, and must pick one of 18 legal moves. "
         "Max 30 turns per puzzle; reaching the limit counts as not solved. The cube engine and exact shortest-solution "
         "search (BFS, meet-in-the-middle) are implemented from scratch in `engine.py`.\n")
L.append("## Models\n\n| Model | Type | How it was run |\n|---|---|---|\n"
         "| Jev (`typesafe/jev-1.13`) | System-1 decision model | OpenRouter Decisions API |\n"
         "| Clef (`cloudflare/clef`) | System-1 decision model | OpenRouter Decisions API |\n"
         "| Qwen (`qwen3:0.6b`) | LLM | Ollama, local, thinking disabled |\n"
         "| Gemma (`gemma3:1b`) | LLM | Ollama, local |\n")
L.append("**Deviation from the assignment:** GPT-6 Luna and Claude Opus 5.5 were not used, because the OpenRouter API "
         "key request deadline had passed and the course instructor suggested open-source models on Ollama instead "
         "(see `instructor_email.png`). My laptop has 8 GB RAM and a slow connection, so the local LLMs are the very small "
         "Qwen3 0.6B and Gemma3 1B. Results for the LLMs therefore reflect small models, not frontier-scale ones.\n")
L.append("## Experiment design\n\n"
         "- **Primary benchmark:** 5 puzzles, 4-5 random-turn scrambles, same puzzles for every model (`puzzles_primary.json`).\n"
         "- **Warm-up:** 5 puzzles, 3-4 turns, used to verify the adapters and engine (`puzzles_warmup.json`).\n"
         "- Max 30 turns. Invalid or malformed output costs one turn, the cube is not changed, and it is counted.\n"
         "- Same timeout (180 s) and retry policy (1 retry) for every model. API errors are logged as invalid outputs.\n"
         "- Models run one at a time (not in parallel) so that latency is not distorted on an 8 GB laptop.\n"
         "- Optimality gap = model moves - exact shortest moves, only for solved puzzles. Move metric: 18 moves (quarter and half turns).\n")
L.append("## Results: primary benchmark\n\n" + summary_table(prim) + "\n")
L.append("### Per-trial results (primary)\n\n" + trials_table(prim) + "\n")
if warm:
    L.append("## Results: warm-up\n\n" + summary_table(warm) + "\n")
L.append("## Answers to the experiment questions\n\n"
         f"1. **Which model is fastest in making decisions?** {a1}\n\n"
         f"2. **Which model achieved the highest solve rate?** {a2}\n\n"
         f"3. **Which model found the shortest solutions, and how close to the optimum?** {a3}\n\n"
         f"4. **Did the fastest model also achieve the best solution quality?** {a4}\n\n"
         f"5. **Fast decision model, frontier LLM, or hybrid?** {a5}\n")
L.append("## Limitations\n\n"
         "- Only 5 puzzles per set, so results are indicative, not statistically strong.\n"
         "- Very small local LLMs (0.6B and 1B parameters), not frontier models.\n"
         "- Cloud and local latencies are not directly comparable (network vs local hardware).\n"
         "- The state is given as a raw 54-character string, which may disadvantage all models.\n")
L.append("## Setup\n\n```\npip install fastapi uvicorn httpx python-dotenv\n"
         "copy .env.example .env      # then put your OpenRouter key in .env\n"
         "ollama pull qwen3:0.6b\nollama pull gemma3:1b\n```\n\n"
         "Run the benchmark: `python benchmark.py --set primary` (or `--set warmup`).\n\n"
         "Run the app: `$env:PUZZLE_SET=\"primary\"; python -m uvicorn server:app --port 8000` and open http://localhost:8000\n\n"
         "The API key is read from the `OPENROUTER_API_KEY` environment variable (`.env`, never committed).\n")
L.append("## Files\n\n`engine.py` cube engine + BFS, `models.py` model adapters, `benchmark.py` runner, "
         "`server.py` + `index.html` app, `results_*.json` raw results, `make_readme.py` generates this README.\n")

open("README.md", "w", encoding="utf-8").write("\n".join(L))
print("README.md ")