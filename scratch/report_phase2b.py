"""Phase 2b: Bidirectional H2H (5 games each direction)."""
import json, copy, sys, os, time, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
agents = {}
for v in ['c9', 'original', 'minimal', 'none']:
    agents[v] = build_agent_with_opening(v, route_data)

NUM = 5
env = make("kaggriculture", configuration={"episodeSteps": 720})

keys = ['c9', 'original', 'minimal', 'none']
pairs = [(keys[i], keys[j]) for i in range(len(keys)) for j in range(i+1, len(keys))]

print(f"=== BIDIRECTIONAL H2H ({NUM} games each direction) ===\n")
h2h = {}
for a, b in pairs:
    a_scores, b_scores = [], []
    a_wins = b_wins = ties = 0
    t0 = time.time()
    for _ in range(NUM):
        env.reset()
        env.run([agents[a], agents[b]])
        r = [s.reward for s in env.steps[-1]]
        a_scores.append(r[0])
        b_scores.append(r[1])
        if r[0] > r[1]: a_wins += 1
        elif r[1] > r[0]: b_wins += 1
        else: ties += 1
    elo_a = (a_wins + 0.5*ties) / NUM
    elo_b = (b_wins + 0.5*ties) / NUM
    elapsed = time.time() - t0
    h2h[f"{a}_vs_{b}"] = {
        'a_wins': a_wins, 'b_wins': b_wins, 'ties': ties,
        'elo_a': elo_a, 'elo_b': elo_b,
        'a_mean': statistics.mean(a_scores), 'b_mean': statistics.mean(b_scores),
        'a_median': statistics.median(a_scores), 'b_median': statistics.median(b_scores),
        'a_scores': a_scores, 'b_scores': b_scores,
    }
    print(f"  {a:>8} vs {b:<8}: {a_wins}W-{b_wins}L-{ties}T  (elo {a}={elo_a:.0%}, {b}={elo_b:.0%})  A=${statistics.mean(a_scores):,.0f} B=${statistics.mean(b_scores):,.0f}  ({elapsed:.0f}s)")

print(f"\n=== WIN-RATE MATRIX (row elo vs column) ===\n")
print(f"{'':>12}", end="")
for v in keys: print(f" {v:>10}", end="")
print()
for v1 in keys:
    print(f"{v1:>12}", end="")
    for v2 in keys:
        if v1 == v2:
            print(f" {'---':>10}", end="")
        elif (f"{v1}_vs_{v2}") in h2h:
            print(f" {h2h[f'{v1}_vs_{v2}']['elo_a']:>9.0%}", end="")
        elif (f"{v2}_vs_{v1}") in h2h:
            print(f" {h2h[f'{v2}_vs_{v1}']['elo_b']:>9.0%}", end="")
    print()

# Save (without raw score lists for JSON compat)
save_h2h = {k: {kk: vv for kk, vv in v.items() if kk not in ('a_scores', 'b_scores')}
            for k, v in h2h.items()}
with open('scratch/report_h2h.json', 'w') as f:
    json.dump(save_h2h, f, indent=2)
print(f"\nSaved to scratch/report_h2h.json")
