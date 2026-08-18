import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
import submission

env = make("kaggriculture", configuration={"episodeSteps": 720})
env.reset()

call_count = [0]
day_snapshots = {}
orig_agent = submission.agent

def debug_agent(obs, config=None):
    call_count[0] += 1
    day  = obs.get("day", 0)
    hour = obs.get("hour", 0)
    result = orig_agent(obs, config)
    if day <= 8 and hour == 0 and day not in day_snapshots:
        farm    = obs.get("farms", [{}])[0]
        private = obs.get("private", {}) or {}
        shed    = private.get("shed", {}) or {}
        seeds   = private.get("seeds", {}) or {}
        invs    = private.get("inventories", []) or []
        tiles   = farm.get("tiles", [])
        n_plant = n_p_cow = n_p_empty = n_empty = n_weed = 0
        for row in tiles:
            for t in row:
                if t is None: n_empty += 1
                elif isinstance(t, dict):
                    k = t.get("kind")
                    if k == "PLANT": n_plant += 1
                    elif k == "PASTURE":
                        if t.get("animal") == "COW": n_p_cow += 1
                        else: n_p_empty += 1
                    elif k == "WEED": n_weed += 1
        day_snapshots[day] = {
            "money":   farm.get("money", 0),
            "workers": 1 + len(farm.get("hands", [])),
            "seeds":   {k:v for k,v in seeds.items() if v > 0},
            "shed":    {k:v for k,v in shed.items() if v > 0},
            "invs":    invs,
            "plants":  n_plant, "cows": n_p_cow, "ep": n_p_empty,
            "empty":   n_empty, "weeds": n_weed,
            "market":  result.get("market", []),
            "farmer":  result.get("farmer", []),
            "hands":   result.get("hands", []),
        }
    return result

env.run([debug_agent, "starter"])

for day in sorted(day_snapshots.keys()):
    s = day_snapshots[day]
    print(f"Day {day:2d} | ${s['money']:6.0f} | workers={s['workers']} | "
          f"plants={s['plants']} cows={s['cows']} ep={s['ep']} empty={s['empty']}")
    print(f"       seeds={s['seeds']}  shed={s['shed']}")
    print(f"       inventories={s['invs']}")
    print(f"       market={s['market']}")
    print(f"       farmer={s['farmer']}  hands={s['hands']}")
    print()
