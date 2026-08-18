"""Extended diagnostic: trace full game state at start of each day."""
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
from submission import agent as orig_agent

env = make("kaggriculture", configuration={"episodeSteps": 720})
env.reset()

lines = []

def diag_agent(obs, config=None):
    day  = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if hour == 0:
        farm = obs["farms"][obs["player"]]
        priv = obs.get("private", {}) or {}
        tiles = farm.get("tiles", [])
        bh = len(tiles); bw = len(tiles[0]) if tiles else 10
        half = bh // 2
        shed_set = {(half-1,half-1),(half,half-1),(half-1,half),(half,half)}
        
        plants = weeds = empty = tomato = straw = wheat = carrot = 0
        for y in range(bh):
            for x in range(bw):
                t = tiles[y][x]
                if (x,y) in shed_set or t == "LOCKED": continue
                if t is None: empty += 1
                elif isinstance(t, dict):
                    k = t.get("kind")
                    if k == "PLANT":
                        plants += 1
                        c = t.get("crop","")
                        if c == "TOMATO": tomato += 1
                        elif c == "STRAWBERRY": straw += 1
                        elif c == "WHEAT": wheat += 1
                        elif c == "CARROT": carrot += 1
                    elif k == "WEED": weeds += 1
        
        shed = priv.get("shed", {})
        seeds = priv.get("seeds", {})
        money = farm.get("money", 0)
        nq = len(farm.get("unlocked_quadrants", []))
        
        non_zero_shed = {k:v for k,v in shed.items() if v}
        non_zero_seeds = {k:v for k,v in seeds.items() if v}
        
        lines.append(
            f"Day {day:2d} | ${money:7.0f} | q={nq} | "
            f"plants={plants}(W{wheat}/T{tomato}/S{straw}/C{carrot}) weeds={weeds} empty={empty} | "
            f"shed={non_zero_shed} seeds={non_zero_seeds}"
        )
    
    return orig_agent(obs, config)

env.run([diag_agent, "starter"])

for l in lines:
    print(l)
print(f"\nFinal score: {env.state[0]['reward']}")
