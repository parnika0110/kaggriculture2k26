"""Hand ablation: create variants with 11/10/9 hands.

Variant A: 11 hands (baseline)
Variant B: 10 hands (skip last hire)
Variant C: 9 hands (skip last 2 hires)

Each variant wraps the base agent and suppresses HIRE orders after a limit.
Process-isolated to avoid state contamination.
"""
import json, sys, subprocess

VARIANT = sys.argv[1]
SEED = int(sys.argv[2])

SCRIPT = f'''
import json, sys
sys.path.insert(0, ".")

base_globals = {{}}
exec(open("submission.py", encoding="utf-8").read(), base_globals)
base_agent = base_globals["agent"]

from kaggle_environments import make

MAX_HANDS = {{"A": 11, "B": 10, "C": 9}}["{VARIANT}"]

def agent_wrapper(obs, config=None):
    action = base_agent(obs, config)
    if not isinstance(action, dict):
        return action
    
    # Count current hands
    farm = obs["farms"][obs["player"]]
    n_hands = len(farm.get("hands", []))
    
    # If already at limit, remove all HIRE orders
    if n_hands >= MAX_HANDS:
        market = action.get("market", [])
        if isinstance(market, list):
            new_market = [o for o in market if not (isinstance(o, list) and len(o) > 0 and o[0] == "HIRE")]
            if len(new_market) != len(market):
                action = dict(action)
                action["market"] = new_market
    
    return action

cfg = {{"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": {SEED}}}
env = make("kaggriculture", debug=True, configuration=cfg)
trainer = env.train([None, "starter"])
obs = trainer.reset()
done = False
hires_suppressed = 0
while not done:
    obs_json = json.loads(json.dumps(obs))
    action = agent_wrapper(obs_json)
    # Track hires
    market = action.get("market", [])
    if isinstance(market, list):
        for o in market:
            if isinstance(o, list) and len(o) > 0 and o[0] == "HIRE":
                pass  # Would hire
    obs, reward, done, info = trainer.step(action)

# Count final hands
final_hands = len(obs["farms"][0].get("hands", []))
print(json.dumps({{"score": reward, "final_hands": final_hands}}))
'''

result = subprocess.run(
    [sys.executable, '-X', 'utf8', '-c', SCRIPT],
    capture_output=True, text=True, timeout=120
)
if result.returncode != 0:
    print(json.dumps({{"error": True, "stderr": result.stderr[-200:]}}))
    sys.exit(1)
lines = result.stdout.strip().split('\n')
print(lines[-1])
