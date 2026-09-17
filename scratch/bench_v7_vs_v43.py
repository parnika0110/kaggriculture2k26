"""Benchmark V7 vs V43+C9 head-to-head."""
import json, sys, time
sys.path.insert(0, '.')
from kaggle_environments import make

# Load V43+C9 (submission.py)
v43_globals = {}
exec(open('submission.py', encoding='utf-8').read(), v43_globals)
v43_agent = v43_globals['agent']

# Load V7
v7_globals = {}
exec(open('scratch/v7_agent.py', encoding='utf-8').read(), v7_globals)
v7_agent = v7_globals['agent']

def run_agent(agent_fn, seed, opponent="random"):
    env = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": seed,
    })
    trainer = env.train([None, opponent])
    obs = trainer.reset()
    done = False
    t0 = time.time()
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_fn(obs_json)
        obs, reward, done, info = trainer.step(action)
    elapsed = time.time() - t0
    return reward, elapsed

def run_h2h(agent1_fn, agent2_fn, seed):
    env = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": seed,
    })
    trainer = env.train([agent2_fn])
    obs = trainer.reset()
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent1_fn(obs_json)
        obs, reward, done, info = trainer.step(action)
    score1 = obs['farms'][0]['money']
    score2 = obs['farms'][1]['money']
    return score1, score2

seeds = list(range(20))

# === Solo benchmarks ===
print("=" * 60)
print("SOLO BENCHMARK (vs random)")
print("=" * 60)
v43_scores = []
v7_scores = []
v43_times = []
v7_times = []

for seed in seeds:
    s43, t43 = run_agent(v43_agent, seed)
    s7, t7 = run_agent(v7_agent, seed)
    v43_scores.append(s43)
    v7_scores.append(s7)
    v43_times.append(t43)
    v7_times.append(t7)
    winner = "V7" if s7 > s43 else "V43" if s43 > s7 else "TIE"
    print(f"Seed {seed:2d}: V43=${s43:>9,.0f}  V7=${s7:>9,.0f}  diff=${s7-s43:>+9,.0f}  [{winner}]")

v43_mean = sum(v43_scores) / len(v43_scores)
v7_mean = sum(v7_scores) / len(v7_scores)
print(f"\nV43+C9 Mean: ${v43_mean:,.0f} (avg {sum(v43_times)/len(v43_times):.1f}s)")
print(f"V7 Mean:     ${v7_mean:,.0f} (avg {sum(v7_times)/len(v7_times):.1f}s)")
print(f"Difference:  ${v7_mean - v43_mean:+,.0f} ({(v7_mean-v43_mean)/v43_mean*100:+.1f}%)")

# Count wins
v7_wins = sum(1 for a, b in zip(v43_scores, v7_scores) if b > a)
v43_wins = sum(1 for a, b in zip(v43_scores, v7_scores) if a > b)
ties = len(seeds) - v7_wins - v43_wins
print(f"V7 wins: {v7_wins}/{len(seeds)}  V43 wins: {v43_wins}/{len(seeds)}  Ties: {ties}")

# === H2H: V7 vs V43+C9 ===
print("\n" + "=" * 60)
print("HEAD-TO-HEAD: V7 vs V43+C9 (10 seeds)")
print("=" * 60)
h2h_seeds = seeds[:10]
v7_h2h_wins = 0
v43_h2h_wins = 0
for seed in h2h_seeds:
    s7, s43 = run_h2h(v7_agent, v43_agent, seed)
    winner = "V7" if s7 > s43 else "V43" if s43 > s7 else "TIE"
    if s7 > s43: v7_h2h_wins += 1
    elif s43 > s7: v43_h2h_wins += 1
    print(f"Seed {seed:2d}: V7=${s7:>9,.0f}  V43=${s43:>9,.0f}  diff=${s7-s43:>+9,.0f}  [{winner}]")

print(f"\nH2H: V7 wins {v7_h2h_wins}/{len(h2h_seeds)}  V43 wins {v43_h2h_wins}/{len(h2h_seeds)}")
