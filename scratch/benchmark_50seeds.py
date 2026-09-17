"""50-seed benchmark: C9 vs Original across 50 fixed seeds."""
import json, sys, os, statistics, time
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
SEEDS = list(range(30))
NUM = len(SEEDS)

print("=" * 70)
print(f"50-SEED BENCHMARK: C9 vs Original")
print("=" * 70)

agents = {
    'c9': build_agent_with_opening('c9', route_data),
    'original': build_agent_with_opening('original', route_data),
}

results = []
t0 = time.time()
for i, seed in enumerate(SEEDS):
    scores = {}
    for variant, agent_fn in agents.items():
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        env.run([agent_fn, "starter"])
        scores[variant] = env.steps[-1][0].reward
    
    diff = scores['c9'] - scores['original']
    winner = "C9" if diff > 0 else "Original" if diff < 0 else "Tie"
    results.append({'seed': seed, 'c9': scores['c9'], 'original': scores['original'], 'diff': diff, 'winner': winner})
    
    if (i+1) % 10 == 0:
        elapsed = time.time() - t0
        c9_w = sum(1 for r in results if r['winner'] == 'C9')
        orig_w = sum(1 for r in results if r['winner'] == 'Original')
        print(f"  [{i+1}/{NUM}] C9: {c9_w}  Orig: {orig_w}  ({elapsed:.0f}s)")

elapsed = time.time() - t0
print(f"\nTotal time: {elapsed:.0f}s ({elapsed/NUM:.1f}s per seed)")

# Results
c9_wins = [r for r in results if r['winner'] == 'C9']
orig_wins = [r for r in results if r['winner'] == 'Original']
ties = [r for r in results if r['winner'] == 'Tie']

print(f"\n--- Win rates ---")
print(f"C9 wins: {len(c9_wins)}/{NUM} ({len(c9_wins)/NUM:.1%})")
print(f"Original wins: {len(orig_wins)}/{NUM} ({len(orig_wins)/NUM:.1%})")
print(f"Ties: {len(ties)}/{NUM} ({len(ties)/NUM:.1%})")

# Score statistics
diffs = [r['diff'] for r in results]
c9_scores = [r['c9'] for r in results]
orig_scores = [r['original'] for r in results]

print(f"\n--- Score statistics ---")
print(f"{'':>20} {'C9':>12} {'Original':>12} {'Diff':>12}")
print(f"{'Mean':>20} ${statistics.mean(c9_scores):>11,.0f} ${statistics.mean(orig_scores):>11,.0f} ${statistics.mean(diffs):>+11,.0f}")
print(f"{'Median':>20} ${statistics.median(c9_scores):>11,.0f} ${statistics.median(orig_scores):>11,.0f} ${statistics.median(diffs):>+11,.0f}")
print(f"{'Stdev':>20} ${statistics.stdev(c9_scores):>11,.0f} ${statistics.stdev(orig_scores):>11,.0f} ${statistics.stdev(diffs):>+11,.0f}")
print(f"{'Min':>20} ${min(c9_scores):>11,.0f} ${min(orig_scores):>11,.0f} ${min(diffs):>+11,.0f}")
print(f"{'Max':>20} ${max(c9_scores):>11,.0f} ${max(orig_scores):>11,.0f} ${max(diffs):>+11,.0f}")

# Failure analysis
print(f"\n--- Failure analysis (Original wins) ---")
if orig_wins:
    fail_diffs = [r['diff'] for r in orig_wins]
    fail_sizes = [-d for d in fail_diffs]
    print(f"Failure rate: {len(orig_wins)}/{NUM} ({len(orig_wins)/NUM:.1%})")
    print(f"Avg failure size: ${statistics.mean(fail_sizes):+,.0f}")
    print(f"Max failure size: ${max(fail_sizes):+,.0f}")
    print(f"Min failure size: ${min(fail_sizes):+,.0f}")
    print(f"Failure seeds: {[r['seed'] for r in orig_wins]}")

# Win analysis
print(f"\n--- Win analysis (C9 wins) ---")
if c9_wins:
    win_diffs = [r['diff'] for r in c9_wins]
    print(f"Win rate: {len(c9_wins)}/{NUM} ({len(c9_wins)/NUM:.1%})")
    print(f"Avg win size: ${statistics.mean(win_diffs):+,.0f}")
    print(f"Max win size: ${max(win_diffs):+,.0f}")
    print(f"Min win size: ${min(win_diffs):+,.0f}")

# Distribution of diffs
print(f"\n--- Diff distribution ---")
buckets = {}
for d in diffs:
    b = int(d / 1000) * 1000
    buckets[b] = buckets.get(b, 0) + 1
for b in sorted(buckets):
    bar = "#" * buckets[b]
    print(f"  ${b:>+8,}: {bar} ({buckets[b]})")

# Save results
with open('scratch/benchmark_50seeds.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to scratch/benchmark_50seeds.json")
