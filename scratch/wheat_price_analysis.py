"""Check wheat price at step 0 across seeds and correlate with flip value."""
import json, copy, sys, os, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
SEEDS = list(range(20))  # Test 20 seeds

print("=" * 70)
print("WHEAT PRICE vs FLIP VALUE ACROSS SEEDS")
print("=" * 70)

# Build agents
agents = {
    'c9': build_agent_with_opening('c9', route_data),
    'original': build_agent_with_opening('original', route_data),
}

results = []
for seed in SEEDS:
    # Get wheat price at step 0
    env_price = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env_price.reset()
    obs = copy.deepcopy(env_price.state[0].observation)
    wheat_price = obs.get('market', {}).get('prices', {}).get('WHEAT', 0)
    
    # Run both agents
    scores = {}
    for variant, agent_fn in agents.items():
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        env.run([agent_fn, "starter"])
        scores[variant] = env.steps[-1][0].reward
    
    diff = scores['c9'] - scores['original']
    winner = "C9" if diff > 0 else "Original" if diff < 0 else "Tie"
    results.append({
        'seed': seed, 'wheat_price': wheat_price,
        'c9': scores['c9'], 'original': scores['original'],
        'diff': diff, 'winner': winner,
    })

# Print results
print(f"\n{'Seed':>6} {'Wheat$':>7} {'C9':>10} {'Original':>10} {'Diff':>10} {'Winner':>10}")
print("-" * 60)
for r in results:
    print(f"{r['seed']:>6} ${r['wheat_price']:>5} ${r['c9']:>9,.0f} ${r['original']:>9,.0f} ${r['diff']:>+9,.0f} {r['winner']:>10}")

# Analyze correlation
print(f"\n--- Correlation analysis ---")
c9_wins = [r for r in results if r['winner'] == 'C9']
orig_wins = [r for r in results if r['winner'] == 'Original']

if c9_wins:
    avg_price_c9 = statistics.mean([r['wheat_price'] for r in c9_wins])
    print(f"C9 wins ({len(c9_wins)}): avg wheat price = ${avg_price_c9:.0f}")
if orig_wins:
    avg_price_orig = statistics.mean([r['wheat_price'] for r in orig_wins])
    print(f"Original wins ({len(orig_wins)}): avg wheat price = ${avg_price_orig:.0f}")

# Find threshold
all_prices = sorted(set(r['wheat_price'] for r in results))
for threshold in all_prices:
    above = [r for r in results if r['wheat_price'] >= threshold]
    below = [r for r in results if r['wheat_price'] < threshold]
    if above and below:
        above_c9 = sum(1 for r in above if r['winner'] == 'C9')
        below_c9 = sum(1 for r in below if r['winner'] == 'C9')
        if above_c9 == len(above) or below_c9 == len(below):
            print(f"\n  Threshold ${threshold}: above={above_c9}/{len(above)} C9 wins, below={below_c9}/{len(below)} C9 wins")

# Summary
print(f"\n--- Summary ---")
print(f"Total seeds: {len(results)}")
print(f"C9 wins: {len(c9_wins)}/{len(results)} ({len(c9_wins)/len(results):.0%})")
print(f"Original wins: {len(orig_wins)}/{len(results)} ({len(orig_wins)/len(results):.0%})")
if c9_wins:
    print(f"C9 avg win margin: ${statistics.mean([r['diff'] for r in c9_wins]):+,.0f}")
if orig_wins:
    print(f"Original avg win margin: ${-statistics.mean([r['diff'] for r in orig_wins]):+,.0f}")
print(f"Mean diff (all): ${statistics.mean([r['diff'] for r in results]):+,.0f}")
print(f"Median diff (all): ${statistics.median([r['diff'] for r in results]):+,.0f}")
