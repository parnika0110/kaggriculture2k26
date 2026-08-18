"""Dump the raw obs structure for first few steps to understand the real API."""
import sys, os, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make

env = make("kaggriculture", configuration={"episodeSteps": 720})
env.reset()

steps_captured = []

def dump_agent(obs, config=None):
    day  = obs.get("day", 0)
    hour = obs.get("hour", 0)
    if day == 0 and hour <= 2:
        # Dump the FULL obs as JSON
        steps_captured.append({"day": day, "hour": hour, "obs": dict(obs)})
    return {"farmer": ["PASS"], "hands": [], "market": []}

env.run([dump_agent, "starter"])

for s in steps_captured:
    print(f"\n{'='*60}")
    print(f"DAY={s['day']} HOUR={s['hour']}")
    obs = s["obs"]
    
    # Print top-level keys
    print("Top-level keys:", list(obs.keys()))
    
    # Print farm (player=0)
    farms = obs.get("farms", [])
    if farms:
        farm = farms[0]
        print("\nFarm keys:", list(farm.keys()))
        print("money:", farm.get("money"))
        print("farmer:", farm.get("farmer"))
        print("hands:", farm.get("hands"))
        print("hires_today:", farm.get("hires_today"))
        print("unlocked_quadrants:", farm.get("unlocked_quadrants"))
        tiles = farm.get("tiles", [])
        print("tiles grid shape:", len(tiles), "x", (len(tiles[0]) if tiles else 0))
    
    # Print private
    private = obs.get("private", {}) or {}
    print("\nPrivate keys:", list(private.keys()))
    print("seeds:", private.get("seeds"))
    shed = private.get("shed", {}) or {}
    print("shed:", {k:v for k,v in shed.items() if v})
    invs = private.get("inventories", [])
    print("inventories:", invs)
    
    # Print market
    mkt = obs.get("market", {}) or {}
    print("\nMarket keys:", list(mkt.keys()))
    print("prices:", mkt.get("prices"))
