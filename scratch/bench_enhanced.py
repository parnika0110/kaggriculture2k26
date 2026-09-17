"""Benchmark enhanced V43+C9+V7 vs both baselines."""
import json, sys, time
sys.path.insert(0, '.')
from kaggle_environments import make

# Load enhanced V43+C9 (with V7 features)
enhanced_globals = {}
exec(open('submission.py', encoding='utf-8').read(), enhanced_globals)
enhanced_agent = enhanced_globals['agent']

# Load V43+C9 backup (original)
v43_globals = {}
exec(open('submission_v43c9_backup.py', encoding='utf-8').read(), v43_globals)
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

seeds = list(range(20))

print("=" * 80)
print("THREE-WAY BENCHMARK (vs random)")
print("=" * 80)
e_scores, v43_scores, v7_scores = [], [], []
e_times, v43_times, v7_times = [], [], []

for seed in seeds:
    s_e, t_e = run_agent(enhanced_agent, seed)
    s43, t43 = run_agent(v43_agent, seed)
    s7, t7 = run_agent(v7_agent, seed)
    e_scores.append(s_e); v43_scores.append(s43); v7_scores.append(s7)
    e_times.append(t_e); v43_times.append(t43); v7_times.append(t7)
    
    # Determine winner
    best = max(s_e, s43, s7)
    if s_e == best: winner = "ENHANCED"
    elif s43 == best: winner = "V43"
    else: winner = "V7"
    
    print(f"Seed {seed:2d}: V43=${s43:>9,.0f}  V7=${s7:>9,.0f}  ENH=${s_e:>9,.0f}  [{winner}]")

e_mean = sum(e_scores) / len(e_scores)
v43_mean = sum(v43_scores) / len(v43_scores)
v7_mean = sum(v7_scores) / len(v7_scores)

print(f"\n{'='*40}")
print(f"V43+C9 Mean:     ${v43_mean:,.0f} (avg {sum(v43_times)/len(v43_times):.1f}s)")
print(f"V7 Mean:         ${v7_mean:,.0f} (avg {sum(v7_times)/len(v7_times):.1f}s)")
print(f"ENHANCED Mean:   ${e_mean:,.0f} (avg {sum(e_times)/len(e_times):.1f}s)")
print(f"{'='*40}")
print(f"Enhanced vs V43: ${e_mean - v43_mean:+,.0f} ({(e_mean-v43_mean)/v43_mean*100:+.1f}%)")
print(f"Enhanced vs V7:  ${e_mean - v7_mean:+,.0f} ({(e_mean-v7_mean)/v7_mean*100:+.1f}%)")

# Win counts
e_beats_v43 = sum(1 for a, b in zip(e_scores, v43_scores) if a > b)
e_beats_v7 = sum(1 for a, b in zip(e_scores, v7_scores) if a > b)
print(f"\nEnhanced beats V43: {e_beats_v43}/{len(seeds)}")
print(f"Enhanced beats V7:  {e_beats_v7}/{len(seeds)}")

# Per-seed analysis
print(f"\n{'='*40}")
print("PER-SEED IMPROVEMENT")
print(f"{'='*40}")
total_gain_v43 = 0
total_gain_v7 = 0
for i, seed in enumerate(seeds):
    gain_v43 = e_scores[i] - v43_scores[i]
    gain_v7 = e_scores[i] - v7_scores[i]
    total_gain_v43 += gain_v43
    total_gain_v7 += gain_v7
    print(f"Seed {seed:2d}: vs V43 {gain_v43:>+9,.0f}  vs V7 {gain_v7:>+9,.0f}")

print(f"\nTotal cumulative gain vs V43: ${total_gain_v43:+,.0f}")
print(f"Total cumulative gain vs V7:  ${total_gain_v7:+,.0f}")
