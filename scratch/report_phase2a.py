"""Phase 2a: Benchmark vs starter only (5 games, fast)."""
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

print(f"=== BENCHMARK vs STARTER ({NUM} games each, identical conditions) ===\n")
bench_scores = {}
for v in ['c9', 'original', 'minimal', 'none']:
    scores = []
    t0 = time.time()
    for _ in range(NUM):
        env.reset()
        env.run([agents[v], "starter"])
        scores.append(env.steps[-1][0].reward)
    elapsed = time.time() - t0
    bench_scores[v] = scores
    mean = statistics.mean(scores)
    med = statistics.median(scores)
    sd = statistics.stdev(scores) if len(scores) > 1 else 0
    print(f"  {v:<12} Mean=${mean:>10,.0f}  Median=${med:>10,.0f}  Stdev=${sd:>9,.0f}  Range=[${min(scores):,.0f}, ${max(scores):,.0f}]  ({elapsed:.0f}s)")
print()

# Save
with open('scratch/report_bench.json', 'w') as f:
    json.dump(bench_scores, f)
print("Saved to scratch/report_bench.json")
