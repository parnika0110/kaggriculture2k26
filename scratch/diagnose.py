import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
import submission

def diagnose():
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

        # Snapshot at start of each day
        if hour == 0 and day not in day_snapshots:
            farm    = obs.get("farms", [{}])[0]
            private = obs.get("private", {}) or {}
            shed    = private.get("shed", {}) or {}
            seeds   = private.get("seeds", {}) or {}
            tiles   = farm.get("tiles", [])

            # Count tile types
            n_plant = n_pasture_cow = n_pasture_empty = n_empty = n_weed = 0
            for row in tiles:
                for t in row:
                    if t is None: n_empty += 1
                    elif t == "LOCKED": pass
                    elif isinstance(t, dict):
                        k = t.get("kind")
                        if k == "PLANT": n_plant += 1
                        elif k == "PASTURE":
                            if t.get("animal") == "COW": n_pasture_cow += 1
                            else: n_pasture_empty += 1
                        elif k == "WEED": n_weed += 1

            day_snapshots[day] = {
                "money":   farm.get("money", 0),
                "workers": 1 + len(farm.get("hands", [])),
                "seeds":   dict(seeds),
                "shed":    dict(shed),
                "plants":  n_plant,
                "cows":    n_pasture_cow,
                "empty_p": n_pasture_empty,
                "empty":   n_empty,
                "weeds":   n_weed,
                "market":  result.get("market", []),
                "farmer":  result.get("farmer", []),
                "hands":   result.get("hands", []),
            }

        return result

    env.run([debug_agent, "starter"])

    print(f"\nTotal agent calls: {call_count[0]}")
    print("\n=== Per-Day Snapshots (start of each day) ===")
    for day in sorted(day_snapshots.keys()):
        s = day_snapshots[day]
        print(f"\nDay {day:2d} | ${s['money']:7.0f} | workers={s['workers']} | plants={s['plants']} cows={s['cows']} empty={s['empty']}")
        print(f"       seeds={s['seeds']}  shed={s['shed']}")
        print(f"       market={s['market']}")
        print(f"       farmer={s['farmer']}  hands[0]={s['hands'][0] if s['hands'] else '[]'}")

    # Final state
    final = env.steps[-1]
    print(f"\nFinal reward: Agent=${final[0].reward:.0f} | Starter=${final[1].reward:.0f}")

if __name__ == "__main__":
    diagnose()
