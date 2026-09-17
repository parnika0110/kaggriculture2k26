"""GOOSE ablation: create variants A/B/C/D with -0/-1/-2/-3 GOOSEs.

Each variant wraps the base V43+C9 agent and removes GOOSE purchases.
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

MAX_GOOSE = {{"A": 999, "B": 2, "C": 1, "D": 0}}["{VARIANT}"]

def agent_wrapper(obs, config=None):
    action = base_agent(obs, config)
    if not isinstance(action, dict):
        return action
    market = action.get("market", [])
    if not isinstance(market, list):
        return action
    
    # Count GOOSE purchases in this turn's market orders
    goose_in_order = 0
    for o in market:
        if isinstance(o, list) and len(o) >= 3 and o[0] == "BUY_ANIMAL" and o[1] == "GOOSE":
            goose_in_order += int(o[2])
    
    # Count total GOOSEs already bought this game (from shed + on board)
    private = obs.get("private", {{}})
    shed = private.get("shed", {{}})
    farm = obs["farms"][obs["player"]]
    goose_in_shed = shed.get("GOOSE", 0)
    goose_on_board = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") == "GOOSE":
                goose_on_board += 1
    
    total_goose = goose_in_shed + goose_on_board
    
    # If adding this purchase would exceed the limit, remove GOOSE orders
    if total_goose + goose_in_order > MAX_GOOSE:
        new_market = []
        for o in market:
            if isinstance(o, list) and len(o) >= 3 and o[0] == "BUY_ANIMAL" and o[1] == "GOOSE":
                # Skip this GOOSE purchase (or reduce quantity)
                remaining = MAX_GOOSE - total_goose
                if remaining > 0:
                    new_market.append(["BUY_ANIMAL", "GOOSE", min(int(o[2]), remaining)])
                # else skip entirely
            else:
                new_market.append(o)
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
while not done:
    obs_json = json.loads(json.dumps(obs))
    action = agent_wrapper(obs_json)
    obs, reward, done, info = trainer.step(action)

# Count final GOOSEs
final_farm = obs["farms"][0]
final_goose = 0
for row in final_farm["tiles"]:
    for tile in row:
        if isinstance(tile, dict) and tile.get("animal") == "GOOSE":
            final_goose += 1

# Count EGGs in shed
final_eggs = obs["private"]["shed"].get("EGG", 0)

print(json.dumps({{"score": reward, "final_goose": final_goose, "final_eggs": final_eggs}}))
'''

result = subprocess.run(
    [sys.executable, '-X', 'utf8', '-c', SCRIPT],
    capture_output=True, text=True, timeout=120
)
if result.returncode != 0:
    print(json.dumps({{"error": True}}))
    sys.exit(1)
lines = result.stdout.strip().split('\n')
print(lines[-1])
