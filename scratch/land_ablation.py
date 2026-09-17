"""Land ablation runner."""
import json, sys, subprocess

VARIANT = sys.argv[1]
SEED = int(sys.argv[2])

BLOCK_MAP = {"A": set(), "B": {"NE"}, "C": {"SW"}, "D": {"NE", "SW"}}
BLOCK = json.dumps(list(BLOCK_MAP[VARIANT]))

SCRIPT = f'''
import json, sys
sys.path.insert(0, ".")

base_globals = {{}}
exec(open("submission.py", encoding="utf-8").read(), base_globals)
base_agent = base_globals["agent"]

from kaggle_environments import make

BLOCK = set({BLOCK})

def agent_wrapper(obs, config=None):
    action = base_agent(obs, config)
    if not isinstance(action, dict):
        return action
    market = action.get("market", [])
    if not isinstance(market, list):
        return action
    farm = obs["farms"][obs["player"]]
    unlocked = farm.get("unlocked_quadrants", ["NW"])
    n_unlocked = len(unlocked) - 1
    quadrant_map = dict([(0, "NE"), (1, "SW"), (2, "SE")])
    new_market = []
    removed = False
    for o in market:
        if isinstance(o, list) and len(o) > 0 and o[0] == "BUY_LAND":
            if n_unlocked < 3:
                would_unlock = quadrant_map.get(n_unlocked)
                if would_unlock in BLOCK:
                    removed = True
                    continue
        new_market.append(o)
    if removed:
        action = dict(action)
        action["market"] = new_market
    return action

cfg = dict(episodeSteps=720, boardSize=10, turnsPerDay=24,
           shedCapacity=100, maxMarketOrdersPerTurn=10,
           farmHandCostMult=1, seed={SEED})
env = make("kaggriculture", debug=True, configuration=cfg)
trainer = env.train([None, "starter"])
obs = trainer.reset()
done = False
while not done:
    obs_json = json.loads(json.dumps(obs))
    action = agent_wrapper(obs_json)
    obs, reward, done, info = trainer.step(action)
final_farm = obs["farms"][0]
final_unlocked = final_farm["unlocked_quadrants"]
final_animals = 0
for row in final_farm["tiles"]:
    for tile in row:
        if isinstance(tile, dict) and "animal" in tile:
            final_animals += 1
print(json.dumps(dict(score=reward, unlocked=final_unlocked, animals=final_animals)))
'''

result = subprocess.run(
    [sys.executable, '-X', 'utf8', '-c', SCRIPT],
    capture_output=True, text=True, timeout=120
)
if result.returncode != 0:
    print(json.dumps({"error": True}))
    sys.exit(1)
lines = result.stdout.strip().split('\n')
print(lines[-1])
