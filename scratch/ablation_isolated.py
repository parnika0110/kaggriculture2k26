"""Process-isolated ablation benchmark.

Each game runs in a separate subprocess to avoid global state contamination.
The V43+C9 agent has persistent state (_IMPL, _R148_PENDING, etc.) that
accumulates across runs, making same-seed results differ between runs.

Usage: python ablation_isolated.py <variant> <seed>
  variant: A, B, C, or D
  seed: integer
Returns: score as a float on stdout
"""
import json, sys, subprocess, os

VARIANT = sys.argv[1]
SEED = int(sys.argv[2])

AGENT_SCRIPT = f'''
import json, sys
sys.path.insert(0, ".")

# Load base agent
base_globals = {{}}
exec(open("submission_v43c9_backup.py", encoding="utf-8").read(), base_globals)
base_agent = base_globals["agent"]

# Load V7 helper functions from enhanced agent
enhanced_globals = {{}}
exec(open("submission.py", encoding="utf-8").read(), enhanced_globals)
frontload_fn = enhanced_globals["_v7_frontload"]
advance_sales_fn = enhanced_globals["_v7_advance_sales"]
future_market_fn = enhanced_globals["_v7_future_market"]
standard_fn = enhanced_globals["_v7_standard"]

from kaggle_environments import make

def agent_a(obs, config=None):
    return base_agent(obs, config)

def agent_b(obs, config=None):
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = frontload_fn(obs, m, None, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

def agent_c(obs, config=None):
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = advance_sales_fn(obs, m, future_market_fn, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

def agent_d(obs, config=None):
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = advance_sales_fn(obs, m, future_market_fn, None)
            if len(new) > 1:
                new = frontload_fn(obs, new, None, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

agents = {{"A": agent_a, "B": agent_b, "C": agent_c, "D": agent_d}}
agent_fn = agents["{VARIANT}"]

cfg = {{"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": {SEED}}}
env = make("kaggriculture", debug=True, configuration=cfg)
trainer = env.train([None, "random"])
obs = trainer.reset()
done = False
while not done:
    obs_json = json.loads(json.dumps(obs))
    action = agent_fn(obs_json)
    obs, reward, done, info = trainer.step(action)
print(reward)
'''

result = subprocess.run(
    [sys.executable, '-X', 'utf8', '-c', AGENT_SCRIPT],
    capture_output=True, text=True, timeout=120
)
if result.returncode != 0:
    print(f"ERROR: {result.stderr[-200:]}", file=sys.stderr)
    sys.exit(1)
# Print just the score (last line of stdout)
lines = result.stdout.strip().split('\n')
print(lines[-1])
