# Rubik's Cube Race: Fast Decision Models vs Frontier-style LLMs

**Student:** Dania Khan | **Roll No:** 23k-0072 | **Course:** AI Engineering, Assignment 02

**Repository:** https://github.com/daniakhan123/rubik-cube-race

## Demo video

[Watch the screen recording](demo.mp4)  (file `demo.mp4` in this repo)

The recording shows the in-progress stage, the completion stage, and the final statistics. Name and roll number are visible on screen throughout.

## What this project does

Four models play the same scrambled 3x3 Rubik's Cube. Each turn the model receives the cube state (54-character facelet string) and recent moves, and must pick one of 18 legal moves. Max 30 turns per puzzle; reaching the limit counts as not solved. The cube engine and exact shortest-solution search (BFS, meet-in-the-middle) are implemented from scratch in `engine.py`.

## Models

| Model | Type | How it was run |
|---|---|---|
| Jev (`typesafe/jev-1.13`) | System-1 decision model | OpenRouter Decisions API |
| Clef (`cloudflare/clef`) | System-1 decision model | OpenRouter Decisions API |
| Qwen (`qwen3:0.6b`) | LLM | Ollama, local, thinking disabled |
| Gemma (`gemma3:1b`) | LLM | Ollama, local |

**Deviation from the assignment:** GPT-6 Luna and Claude Opus 5.5 were not used, because the OpenRouter API key request deadline had passed and the course instructor suggested open-source models on Ollama instead (see `instructor_email.png`). My laptop has 8 GB RAM and a slow connection, so the local LLMs are the very small Qwen3 0.6B and Gemma3 1B. Results for the LLMs therefore reflect small models, not frontier-scale ones.

## Experiment design

- **Primary benchmark:** 5 puzzles, 4-5 random-turn scrambles, same puzzles for every model (`puzzles_primary.json`).
- **Warm-up:** 5 puzzles, 3-4 turns, used to verify the adapters and engine (`puzzles_warmup.json`).
- Max 30 turns. Invalid or malformed output costs one turn, the cube is not changed, and it is counted.
- Same timeout (180 s) and retry policy (1 retry) for every model. API errors are logged as invalid outputs.
- Models run one at a time (not in parallel) so that latency is not distorted on an 8 GB laptop.
- Optimality gap = model moves - exact shortest moves, only for solved puzzles. Move metric: 18 moves (quarter and half turns).

## Results: primary benchmark

| Model | Solve rate | Avg latency/move (s) | Avg total time (s) | Avg moves | Avg optimal gap (solved) | Optimal solves | Invalid |
|---|---|---|---|---|---|---|---|
| Jev | 0% | 1.18 | 35.3 | 30.0 | - | 0 | 0 |
| Clef | 0% | 1.17 | 35.0 | 30.0 | - | 0 | 0 |
| Qwen | 0% | 2.94 | 88.3 | 30.0 | - | 0 | 0 |
| Gemma | 0% | 3.00 | 90.1 | 30.0 | - | 0 | 0 |

### Per-trial results (primary)

| Model | Puzzle | Shortest | Solved | Moves | Gap | Time (s) | Invalid |
|---|---|---|---|---|---|---|---|
| Jev | 1 | 4 | no | 30 | - | 35.3 | 0 |
| Clef | 1 | 4 | no | 30 | - | 35.0 | 0 |
| Qwen | 1 | 4 | no | 30 | - | 88.3 | 0 |
| Gemma | 1 | 4 | no | 30 | - | 90.1 | 0 |

## Results: warm-up

| Model | Solve rate | Avg latency/move (s) | Avg total time (s) | Avg moves | Avg optimal gap (solved) | Optimal solves | Invalid |
|---|---|---|---|---|---|---|---|
| Jev | 0% | 1.23 | 37.0 | 30.0 | - | 0 | 0 |
| Clef | 0% | 1.40 | 41.9 | 30.0 | - | 0 | 0 |

## Answers to the experiment questions

1. **Which model is fastest in making decisions?** **Clef** was the fastest decision-maker at 1.17 s per move (average over all moves and puzzles). Note: Jev, Clef (OpenRouter, cloud) and Gemma, Qwen (Ollama, local CPU/GPU of an 8 GB laptop) run on different infrastructure, so latency reflects both the model and where it runs.

2. **Which model achieved the highest solve rate?** No model solved any primary puzzle within 30 moves (solve rate 0% for all models).

3. **Which model found the shortest solutions, and how close to the optimum?** Since no model solved a puzzle, an optimality gap cannot be computed for any model (gap = model moves - exact shortest moves, defined only for solved puzzles). The exact shortest distances (BFS) are listed per puzzle in the trial table.

4. **Did the fastest model also achieve the best solution quality?** No. The fastest model (Clef) did not solve more puzzles than the others: nobody solved any, so speed did not translate into better solution quality.

5. **Fast decision model, frontier LLM, or hybrid?** I would use a **hybrid agent**: a fast decision model for cheap, low-latency routing and classification steps, and a stronger reasoning model (or a dedicated solver) when multi-step planning is needed. Evidence from this run: the fastest model (Clef, 1.17 s/move) reached a solve rate of 0%, and the best-performing model was Jev (0%). Speed alone did not guarantee solution quality, which supports using each kind of model where it is strong.

## Limitations

- Only 5 puzzles per set, so results are indicative, not statistically strong.
- Very small local LLMs (0.6B and 1B parameters), not frontier models.
- Cloud and local latencies are not directly comparable (network vs local hardware).
- The state is given as a raw 54-character string, which may disadvantage all models.

## Setup

```
pip install fastapi uvicorn httpx python-dotenv
copy .env.example .env      # then put your OpenRouter key in .env
ollama pull qwen3:0.6b
ollama pull gemma3:1b
```

Run the benchmark: `python benchmark.py --set primary` (or `--set warmup`).

Run the app: `$env:PUZZLE_SET="primary"; python -m uvicorn server:app --port 8000` and open http://localhost:8000

The API key is read from the `OPENROUTER_API_KEY` environment variable (`.env`, never committed).

## Files

`engine.py` cube engine + BFS, `models.py` model adapters, `benchmark.py` runner, `server.py` + `index.html` app, `results_*.json` raw results, `make_readme.py` generates this README.
