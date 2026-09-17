"""Run deterministic process-isolated ablation benchmark."""
import subprocess, sys, time, math, json
from concurrent.futures import ProcessPoolExecutor, as_completed

SEEDS = list(range(20))
VARIANTS = ["A", "B", "C", "D"]

def run_one(variant, seed):
    result = subprocess.run(
        [sys.executable, '-X', 'utf8', 'scratch/ablation_isolated_det.py', variant, str(seed)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        return None
    lines = result.stdout.strip().split('\n')
    try:
        return float(lines[-1])
    except ValueError:
        return None

results = {v: [None] * len(SEEDS) for v in VARIANTS}
total_games = len(SEEDS) * len(VARIANTS)
completed = 0
t0 = time.time()

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = {}
    for seed in SEEDS:
        for variant in VARIANTS:
            future = executor.submit(run_one, variant, seed)
            futures[future] = (variant, seed)
    
    for future in as_completed(futures):
        variant, seed = futures[future]
        try:
            score = future.result(timeout=120)
        except Exception:
            score = None
        results[variant][seed] = score
        completed += 1
        elapsed = time.time() - t0
        eta = elapsed / completed * (total_games - completed) if completed > 0 else 0
        score_str = f"${score:,.0f}" if score else "ERROR"
        print(f"\r  [{completed}/{total_games}] {variant} seed {seed:2d} = {score_str:>12s}  ETA: {eta:.0f}s", end="", flush=True)

print(f"\n\nCompleted in {time.time()-t0:.0f}s")

# ============================================================
# Per-seed table
# ============================================================
print("\n" + "=" * 90)
print("PER-SEED TABLE (deterministic, starter opponent, process-isolated)")
print("=" * 90)
print(f"{'seed':>4s} | {'A (base)':>12s} | {'B (+front)':>12s} | {'C (+adv)':>12s} | {'D (+both)':>12s} | winner")
print("-" * 90)
for i, seed in enumerate(SEEDS):
    vals = [results[v][i] for v in VARIANTS]
    if any(v is None for v in vals):
        print(f"{seed:4d} | " + " | ".join(f"{'ERROR':>12s}" if v is None else f"${v:>10,.0f}" for v in vals) + " | ERROR")
        continue
    best = max(vals)
    w = VARIANTS[vals.index(best)]
    print(f"{seed:4d} | " + " | ".join(f"${v:>10,.0f}" for v in vals) + f" | {w}")

# ============================================================
# Statistics
# ============================================================
def stats(scores):
    valid = [s for s in scores if s is not None]
    if not valid:
        return {"mean": 0, "median": 0, "min": 0, "max": 0, "stdev": 0, "total": 0, "n": 0}
    n = len(valid)
    mean = sum(valid) / n
    median = sorted(valid)[n // 2]
    mn = min(valid)
    mx = max(valid)
    var = sum((x - mean) ** 2 for x in valid) / n
    stdev = math.sqrt(var)
    total = sum(valid)
    return {"mean": mean, "median": median, "min": mn, "max": mx, "stdev": stdev, "total": total, "n": n}

print("\n" + "=" * 90)
print("STATISTICAL SUMMARY")
print("=" * 90)
print(f"{'Metric':<15s} | {'A (base)':>12s} | {'B (+front)':>12s} | {'C (+adv)':>12s} | {'D (+both)':>12s}")
print("-" * 90)
for metric in ["mean", "median", "min", "max", "stdev", "total"]:
    vals = [stats(results[v])[metric] for v in VARIANTS]
    label = metric if metric != "total" else "total_score"
    print(f"{label:<15s} | " + " | ".join(f"${v:>10,.0f}" for v in vals))

# ============================================================
# Pairwise win/loss/tie
# ============================================================
print("\n" + "=" * 90)
print("PAIRWISE WIN/LOSS/TIE COUNTS")
print("=" * 90)
for i, x_name in enumerate(VARIANTS):
    for y_name in VARIANTS[i+1:]:
        x_scores = [s for s in results[x_name] if s is not None]
        y_scores = [s for s in results[y_name] if s is not None]
        n = min(len(x_scores), len(y_scores))
        wins = sum(1 for x, y in zip(x_scores[:n], y_scores[:n]) if x > y)
        losses = sum(1 for x, y in zip(x_scores[:n], y_scores[:n]) if x < y)
        ties = n - wins - losses
        diff = stats(x_scores)["mean"] - stats(y_scores)["mean"]
        print(f"  {x_name} vs {y_name}: {wins}W-{losses}L-{ties}T  (mean diff: ${diff:+,.0f})")

# ============================================================
# Save results
# ============================================================
output = {
    "seeds": SEEDS,
    "results": {v: [s for s in scores] for v, scores in results.items()},
    "stats": {v: stats(scores) for v, scores in results.items()},
}
with open("scratch/ablation_results_det.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to scratch/ablation_results_det.json")
