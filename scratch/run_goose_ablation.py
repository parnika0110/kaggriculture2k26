"""Run GOOSE ablation benchmark on 20 seeds."""
import subprocess, sys, time, math, json

SEEDS = list(range(20))
VARIANTS = ["A", "B", "C", "D"]

def run_one(variant, seed):
    result = subprocess.run(
        [sys.executable, '-X', 'utf8', 'scratch/goose_ablation.py', variant, str(seed)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        return None
    lines = result.stdout.strip().split('\n')
    try:
        return json.loads(lines[-1])
    except (json.JSONDecodeError, ValueError):
        return None

results = {v: [None] * len(SEEDS) for v in VARIANTS}
total_games = len(SEEDS) * len(VARIANTS)
completed = 0
t0 = time.time()

for seed in SEEDS:
    for variant in VARIANTS:
        data = run_one(variant, seed)
        results[variant][seed] = data
        completed += 1
        elapsed = time.time() - t0
        eta = elapsed / completed * (total_games - completed) if completed > 0 else 0
        score_str = f"${data['score']:,.0f}" if data and 'score' in data else "ERROR"
        goose_str = f" g={data.get('final_goose','?')}" if data else ""
        print(f"\r  [{completed}/{total_games}] {variant} seed {seed:2d} = {score_str:>12s}{goose_str:>5s}  ETA: {eta:.0f}s", end="", flush=True)

print(f"\n\nCompleted in {time.time()-t0:.0f}s")

# Per-seed table
print("\n" + "=" * 100)
print("PER-SEED TABLE (deterministic, starter opponent, process-isolated)")
print("=" * 100)
print(f"{'seed':>4s} | {'A (base)':>12s} {'g':>3s} | {'B (-1)':>12s} {'g':>3s} | {'C (-2)':>12s} {'g':>3s} | {'D (-3)':>12s} {'g':>3s} | winner")
print("-" * 100)
for i, seed in enumerate(SEEDS):
    vals = []
    goose_counts = []
    for v in VARIANTS:
        d = results[v][i]
        if d and 'score' in d:
            vals.append(d['score'])
            goose_counts.append(d.get('final_goose', '?'))
        else:
            vals.append(None)
            goose_counts.append('?')
    
    if any(v is None for v in vals):
        print(f"{seed:4d} | " + " | ".join(f"{'ERROR':>12s}  ? " for _ in VARIANTS) + " | ERROR")
        continue
    
    best = max(vals)
    w = VARIANTS[vals.index(best)]
    parts = []
    for j, v in enumerate(VARIANTS):
        parts.append(f"${vals[j]:>10,.0f} {goose_counts[j]:>2}")
    print(f"{seed:4d} | {'  |  '.join(parts)} | {w}")

# Statistics
def stats(scores):
    valid = [s for s in scores if s is not None]
    if not valid: return {"mean": 0, "median": 0, "min": 0, "max": 0, "stdev": 0, "total": 0}
    n = len(valid)
    mean = sum(valid) / n
    median = sorted(valid)[n // 2]
    var = sum((x - mean) ** 2 for x in valid) / n
    return {"mean": mean, "median": median, "min": min(valid), "max": max(valid),
            "stdev": math.sqrt(var), "total": sum(valid)}

print("\n" + "=" * 100)
print("STATISTICAL SUMMARY")
print("=" * 100)
print(f"{'Metric':<15s} | {'A (base)':>12s} | {'B (-1)':>12s} | {'C (-2)':>12s} | {'D (-3)':>12s}")
print("-" * 100)
for metric in ["mean", "median", "min", "max", "stdev", "total"]:
    vals = [stats([results[v][i]['score'] if results[v][i] and 'score' in results[v][i] else None for i in range(len(SEEDS))])[metric] for v in VARIANTS]
    label = metric if metric != "total" else "total_score"
    print(f"{label:<15s} | " + " | ".join(f"${v:>10,.0f}" for v in vals))

# Pairwise
print("\n" + "=" * 100)
print("PAIRWISE WIN/LOSS/TIE COUNTS (vs A)")
print("=" * 100)
a_scores = [results["A"][i]["score"] if results["A"][i] and "score" in results["A"][i] else None for i in range(len(SEEDS))]
for v_name in ["B", "C", "D"]:
    v_scores = [results[v_name][i]["score"] if results[v_name][i] and "score" in results[v_name][i] else None for i in range(len(SEEDS))]
    n = min(len(a_scores), len(v_scores))
    valid = [(a, v) for a, v in zip(a_scores[:n], v_scores[:n]) if a is not None and v is not None]
    wins = sum(1 for a, v in valid if v > a)
    losses = sum(1 for a, v in valid if v < a)
    ties = len(valid) - wins - losses
    diff = stats(v_scores)["mean"] - stats(a_scores)["mean"]
    print(f"  A vs {v_name}: {wins}W-{losses}L-{ties}T  (mean diff: ${diff:+,.0f})")
