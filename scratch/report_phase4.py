"""Phase 4: Investigate the seed=8042 outlier."""
import json, sys, os, copy
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()
agents = {v: build_agent_with_opening(v, route_data) for v in ['c9', 'original']}

# Run seed=8042 H2H (C9 vs Original directly)
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 8042})
env.reset()
env.run([agents['c9'], agents['original']])
res = [s.reward for s in env.steps[-1]]
print(f"seed=8042 H2H: C9=${res[0]:,.0f}  Original=${res[1]:,.0f}  diff=${res[0]-res[1]:+,.0f}")

# Also check a few other seeds H2H
for seed in [42, 1042, 2042, 8042, 9042]:
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.reset()
    env.run([agents['c9'], agents['original']])
    res = [s.reward for s in env.steps[-1]]
    print(f"seed={seed:<6} H2H: C9=${res[0]:>10,.0f}  Orig=${res[1]:>10,.0f}  diff=${res[0]-res[1]:>+10,.0f}")

# Check what route each variant selected on seed=8042
print("\n--- Route selection on seed=8042 ---")
for v_name, agent_fn in agents.items():
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 8042})
    env.reset()
    obs = copy.deepcopy(env.state[0].observation)
    action = agent_fn(obs)
    # The agent internally selects a route; we can check the state
    print(f"  {v_name}: step 0 market = {action.get('market', [])}")

# Run starter benchmark on seed=8042 to see both scores
print("\n--- vs Starter on seed=8042 ---")
for v_name, agent_fn in agents.items():
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 8042})
    env.reset()
    env.run([agent_fn, "starter"])
    res = [s.reward for s in env.steps[-1]]
    print(f"  {v_name}: ${res[0]:>10,.0f}  (starter: ${res[1]:>10,.0f})")
