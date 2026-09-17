"""Test wheat flip value on all routes across fixed seeds to find correct decision boundary."""
import json, copy, sys, os, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
SEEDS = list(range(10))  # 0-9
NUM_SEEDS = len(SEEDS)

print("=" * 70)
print("WHEAT FLIP VALUE: Testing all routes across 10 seeds")
print("=" * 70)

# Build both agents
agents = {
    'c9': build_agent_with_opening('c9', route_data),
    'original': build_agent_with_opening('original', route_data),
}

# Run both agents on all seeds
results = {}
for seed in SEEDS:
    for variant, agent_fn in agents.items():
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        results.setdefault(seed, {})[variant] = score

# Analyze
print(f"\n{'Seed':>6} {'C9':>10} {'Original':>10} {'Diff':>10} {'Winner':>10}")
print("-" * 50)
c9_wins = orig_wins = ties = 0
diffs = []
for seed in SEEDS:
    c9_s = results[seed]['c9']
    orig_s = results[seed]['original']
    diff = c9_s - orig_s
    diffs.append(diff)
    winner = "C9" if diff > 0 else "Original" if diff < 0 else "Tie"
    if diff > 0: c9_wins += 1
    elif diff < 0: orig_wins += 1
    else: ties += 1
    print(f"{seed:>6} ${c9_s:>9,.0f} ${orig_s:>9,.0f} ${diff:>+9,.0f} {winner:>10}")

print(f"\nC9 wins: {c9_wins}/{NUM_SEEDS}")
print(f"Original wins: {orig_wins}/{NUM_SEEDS}")
print(f"Mean diff: ${statistics.mean(diffs):+,.0f}")
print(f"Median diff: ${statistics.median(diffs):+,.0f}")

# Check BAKERY classification
bakery = {101,103,104,105,106,107,108,109,111,119,120}
dynamic_bakery = set()
for entry in route_data.get('shops', []):
    if 'BAKERY' in entry.get('shops', []):
        dynamic_bakery.add(entry.get('route'))

print(f"\nBAKERY routes (hardcoded): {sorted(bakery)}")
print(f"BAKERY routes (dynamic): {sorted(dynamic_bakery)}")
print(f"Match: {bakery == dynamic_bakery}")

# Check if any seed selected a BAKERY route
print(f"\n--- Route selection across seeds ---")
for seed in SEEDS:
    # Trace route selection
    source = load_notebook_agent().replace('\r\n', '\n')
    ns = {'__builtins__': __builtins__}
    exec(compile(source, '<trace>', 'exec'), ns)
    impl = ns['_IMPL']
    
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    obs = copy.deepcopy(env.state[0].observation)
    agents['c9'](obs)  # Run one step to trigger route selection
    
    # Get route from chassis
    chassis = impl.chassis
    st = chassis.players.get(0, {})
    route = st.get('route', None)
    is_bakery = route in bakery if route else False
    print(f"  Seed {seed:>2}: route={route}  BAKERY={is_bakery}")
