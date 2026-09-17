"""Phase 3: C9 independence test with fixed seeds."""
import json, sys, os, time, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
agent = build_agent_with_opening('c9', route_data)

env = make("kaggriculture", configuration={"episodeSteps": 720})
NUM = 10

print(f"=== C9 INDEPENDENCE TEST ({NUM} fixed-seed games vs starter) ===\n")
scores = []
seeds = []
for i in range(NUM):
    seed = i * 1000 + 42
    env2 = make('kaggriculture', configuration={'episodeSteps': 720, 'seed': seed})
    env2.reset()
    env2.run([agent, "starter"])
    s = env2.steps[-1][0].reward
    scores.append(s)
    seeds.append(seed)
    bar = "#" * max(1, int(s / 5000))
    print(f"  seed={seed:<8}  ${s:>10,.0f}  {bar}")

mean = statistics.mean(scores)
med = statistics.median(scores)
sd = statistics.stdev(scores) if len(scores) > 1 else 0
print(f"\n  Mean:   ${mean:>10,.0f}")
print(f"  Median: ${med:>10,.0f}")
print(f"  Stdev:  ${sd:>10,.0f}")
print(f"  Min:    ${min(scores):>10,.0f}")
print(f"  Max:    ${max(scores):>10,.0f}")
print(f"  Range:  ${max(scores) - min(scores):>10,.0f}")

# Also test Original for comparison
agent_orig = build_agent_with_opening('original', route_data)
scores_orig = []
for i in range(NUM):
    seed = i * 1000 + 42
    env2 = make('kaggriculture', configuration={'episodeSteps': 720, 'seed': seed})
    env2.reset()
    env2.run([agent_orig, "starter"])
    scores_orig.append(env2.steps[-1][0].reward)

print(f"\n=== ORIGINAL (same seeds for comparison) ===\n")
for i, (seed, sc, so) in enumerate(zip(seeds, scores, scores_orig)):
    diff = sc - so
    winner = "C9" if diff > 0 else "Orig" if diff < 0 else "Tie"
    bar = "#" * max(1, int(abs(diff) / 10))
    sign = "+" if diff >= 0 else ""
    print(f"  seed={seed:<8}  C9=${sc:>10,.0f}  Orig=${so:>10,.0f}  diff={sign}${diff:>8,.0f}  {bar}")

print(f"\n  C9 mean:   ${statistics.mean(scores):>10,.0f}")
print(f"  Orig mean: ${statistics.mean(scores_orig):>10,.0f}")
print(f"  Mean diff: ${statistics.mean(scores) - statistics.mean(scores_orig):>+10,.0f}")
