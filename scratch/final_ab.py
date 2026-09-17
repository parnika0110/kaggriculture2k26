"""Final A/B comparison: C9 vs V43 Original, 50 games each direction + vs starter."""
import json, sys, os, time, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
print("Building agents...")
agents = {
    'c9': build_agent_with_opening('c9', route_data),
    'original': build_agent_with_opening('original', route_data),
}
print("Done.\n")

NUM = 50
env = make("kaggriculture", configuration={"episodeSteps": 720})

# ── H2H: C9 vs Original ──
print(f"=== H2H: C9 vs Original ({NUM} games) ===")
a_wins = b_wins = ties = 0
a_scores = []
b_scores = []
t0 = time.time()
for i in range(NUM):
    env.reset()
    env.run([agents['c9'], agents['original']])
    r = [s.reward for s in env.steps[-1]]
    a_scores.append(r[0])
    b_scores.append(r[1])
    if r[0] > r[1]: a_wins += 1
    elif r[1] > r[0]: b_wins += 1
    else: ties += 1
    if (i+1) % 10 == 0:
        elapsed = time.time() - t0
        print(f"  [{i+1}/{NUM}] C9 wins: {a_wins}  Orig wins: {b_wins}  Ties: {ties}  ({elapsed:.0f}s)")

elo_c9 = (a_wins + 0.5*ties) / NUM
elo_orig = (b_wins + 0.5*ties) / NUM
print(f"\n  C9:    {a_wins}W-{b_wins}L-{ties}T  elo={elo_c9:.1%}  mean=${statistics.mean(a_scores):,.0f}  median=${statistics.median(a_scores):,.0f}")
print(f"  Orig:  {b_wins}W-{a_wins}L-{ties}T  elo={elo_orig:.1%}  mean=${statistics.mean(b_scores):,.0f}  median=${statistics.median(b_scores):,.0f}")
print(f"  Score diff: ${statistics.mean(a_scores) - statistics.mean(b_scores):+,.0f}")

# Score distribution
print(f"\n  Score distribution (C9 - Original):")
diffs = [a - b for a, b in zip(a_scores, b_scores)]
lo, hi = min(diffs), max(diffs)
bucket = max(500, int((hi - lo) / 10))
buckets = {}
for d in diffs:
    b = int((d - lo) / bucket) * bucket + lo
    buckets[b] = buckets.get(b, 0) + 1
for b in sorted(buckets):
    bar = "#" * buckets[b]
    print(f"    ${b:>+8,}: {bar} ({buckets[b]})")

# ── vs Starter ──
for variant in ['c9', 'original']:
    print(f"\n=== {variant.upper()} vs Starter ({NUM} games) ===")
    scores = []
    t0 = time.time()
    for i in range(NUM):
        env.reset()
        env.run([agents[variant], "starter"])
        scores.append(env.steps[-1][0].reward)
        if (i+1) % 10 == 0:
            elapsed = time.time() - t0
            print(f"  [{i+1}/{NUM}] mean=${statistics.mean(scores):,.0f}  ({elapsed:.0f}s)")
    print(f"  Final: mean=${statistics.mean(scores):,.0f}  median=${statistics.median(scores):,.0f}  stdev=${statistics.stdev(scores):,.0f}")
    print(f"  Range: ${min(scores):,.0f} - ${max(scores):,.0f}")

# ── Summary ──
print(f"\n{'='*70}")
print(f"FINAL SUMMARY")
print(f"{'='*70}")
print(f"H2H C9 vs Original: {a_wins}-{b_wins}-{ties} ({elo_c9:.1%} elo for C9)")
print(f"C9 mean score (H2H): ${statistics.mean(a_scores):,.0f}")
print(f"Original mean score (H2H): ${statistics.mean(b_scores):,.0f}")
print(f"C9 advantage: ${statistics.mean(a_scores) - statistics.mean(b_scores):+,.0f}")

# Save results
results = {
    'h2h': {'c9_wins': a_wins, 'orig_wins': b_wins, 'ties': ties,
            'elo_c9': elo_c9, 'c9_mean': statistics.mean(a_scores),
            'orig_mean': statistics.mean(b_scores)},
    'num_games': NUM,
}
with open('scratch/final_ab_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to scratch/final_ab_results.json")
