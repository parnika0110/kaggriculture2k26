import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
import submission

env = make("kaggriculture", configuration={"episodeSteps": 720})
env.reset()

captured = {}

orig_agent = submission.agent

def debug_agent(obs, config=None):
    day  = obs.get("day", 0)
    hour = obs.get("hour", 0)
    result = orig_agent(obs, config)
    
    if day == 1 and hour <= 3:
        farm    = obs.get("farms", [{}])[0]
        private = obs.get("private", {}) or {}
        tiles   = farm.get("tiles", [])
        board_size = len(tiles)
        half = board_size // 2
        shed_set = {(half-1, half-1), (half, half-1), (half-1, half), (half, half)}
        farmer_pos = tuple(farm.get("farmer", []))
        hands = farm.get("hands", [])
        invs  = private.get("inventories", [])
        shed  = private.get("shed", {}) or {}
        key = f"d{day}h{hour}"
        captured[key] = {
            "board_size": board_size,
            "half": half,
            "shed_set": shed_set,
            "farmer_pos": farmer_pos,
            "at_shed": farmer_pos in shed_set,
            "farmer_inv": invs[0] if invs else "N/A",
            "shed_cows": shed.get("COW", 0),
            "action": result.get("farmer"),
            "hands": hands,
            "hands_invs": invs[1:] if len(invs) > 1 else [],
        }
    return result

env.run([debug_agent, "starter"])

for k, v in sorted(captured.items()):
    print(f"\n=== {k} ===")
    for field, val in v.items():
        print(f"  {field}: {val}")
