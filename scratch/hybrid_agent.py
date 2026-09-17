"""Hybrid agent: V43+C9 base + tomato planting on PASS slots.

Wraps the existing V43+C9 agent and replaces PASS actions with tomato
planting/watering/harvesting when free units are available.

Key insight: V43+C9 has 625 PASS actions across a game. We can use ~600 of
these to plant and maintain ~9 tomato plants, adding ~$10K+ revenue.
"""
import json
import sys
import os

# Load V43+C9 agent
_agent_globals = {}
exec(open('submission.py', encoding='utf-8').read(), _agent_globals)
_V43C9 = _agent_globals['agent']

BOARD = 10
SHED = {(4,4),(5,4),(4,5),(5,5)}

def _quad(x, y):
    h = BOARD // 2
    return ("N" if y < h else "S") + ("W" if x < h else "E")

def _pos(farm, idx):
    if idx == 0:
        return tuple(farm["farmer"])
    hands = farm.get("hands", [])
    if 0 <= idx - 1 < len(hands):
        return tuple(hands[idx - 1])
    return None

def _move_to(pos, target):
    if pos == target:
        return None
    x, y = pos
    tx, ty = target
    if x < tx: return ["EAST"]
    if x > tx: return ["WEST"]
    if y < ty: return ["SOUTH"]
    if y > ty: return ["NORTH"]
    return None

def _dist(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# ============================================================
# Persistent state for tomato management
# ============================================================
_TSTATE = {}

def _ts(pid):
    if pid not in _TSTATE:
        _TSTATE[pid] = {
            "planted": set(),       # tiles with tomato plants
            "targets": {},          # unit_idx -> (x,y) heading to plant
            "has_seed": set(),      # units carrying tomato seed
        }
    return _TSTATE[pid]

def _scan_tiles(farm, unlocked):
    """Quick scan for tomatoes and empty tiles."""
    tomatoes = []       # (x, y, tile) - tomato plants
    unwatered = []      # (x, y) - unwatered plants
    harvestable = []    # (x, y, tile) - anything with yield > 0
    empty = []          # (x, y) - empty plantable tiles

    for y in range(BOARD):
        for x in range(BOARD):
            if (x, y) in SHED:
                continue
            tile = farm["tiles"][y][x]
            if tile is None and _quad(x, y) in unlocked:
                empty.append((x, y))
            elif isinstance(tile, dict):
                kind = tile.get("kind", "")
                if kind == "PLANT" and tile.get("crop") == "TOMATO":
                    tomatoes.append((x, y, tile))
                    if not tile.get("watered_today"):
                        unwatered.append((x, y))
                if kind == "PLANT" and tile.get("yield_units", 0) > 0:
                    harvestable.append((x, y, tile))
                # Also harvest any animal products
                if "animal" in tile and tile.get("yield_units", 0) > 0:
                    harvestable.append((x, y, tile))

    return {
        "tomatoes": tomatoes,
        "unwatered": unwatered,
        "harvestable": harvestable,
        "empty": empty,
    }

# ============================================================
# Tomato layer: replaces PASS with planting/watering/harvesting
# ============================================================
def _tomato_layer(observation, action):
    """Modify action to use PASS slots for tomato work."""
    pid = observation["player"]
    day = observation["step"] // 24
    hour = observation["step"] % 24
    farm = observation["farms"][pid]
    private = observation["private"]
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})
    unlocked = farm["unlocked_quadrants"]
    hands = farm.get("hands", [])
    n_units = 1 + len(hands)

    ts = _ts(pid)
    tiles = _scan_tiles(farm, unlocked)

    # Get current actions
    farmer_act = list(action.get("farmer", ["PASS"]))
    hands_acts = [list(h) for h in action.get("hands", [])]
    all_acts = [farmer_act] + hands_acts

    # Identify PASS units
    pass_units = []
    for i in range(n_units):
        a = all_acts[i]
        if a == ["PASS"] or a == [] or a is None:
            pass_units.append(i)

    if not pass_units:
        return action

    # ============================================================
    # Priority 1: Water our tomato plants
    # ============================================================
    if tiles["unwatered"]:
        for wx, wy in tiles["unwatered"]:
            if not pass_units:
                break
            # Find closest PASS unit
            best_i, best_d = -1, 999
            for i in pass_units:
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                d = _dist(pos_i, (wx, wy))
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos_i = _pos(farm, best_i)
                if pos_i == (wx, wy):
                    all_acts[best_i] = ["WATER"]
                    pass_units.remove(best_i)
                else:
                    move = _move_to(pos_i, (wx, wy))
                    if move:
                        all_acts[best_i] = move
                        pass_units.remove(best_i)

    # ============================================================
    # Priority 2: Harvest our tomatoes
    # ============================================================
    for hx, hy, ht in tiles["harvestable"]:
        if not pass_units:
            break
        # Only harvest tomatoes we planted (or any plant/animal with yield)
        best_i, best_d = -1, 999
        for i in pass_units:
            pos_i = _pos(farm, i)
            if pos_i is None:
                continue
            d = _dist(pos_i, (hx, hy))
            if d < best_d:
                best_d = d
                best_i = i
        if best_i >= 0:
            pos_i = _pos(farm, best_i)
            if pos_i == (hx, hy):
                all_acts[best_i] = ["HARVEST"]
                pass_units.remove(best_i)
            else:
                move = _move_to(pos_i, (hx, hy))
                if move:
                    all_acts[best_i] = move
                    pass_units.remove(best_i)

    # ============================================================
    # Priority 3: Plant tomatoes on empty tiles (days 1-21)
    # ============================================================
    if day >= 1 and day <= 21 and seeds.get("TOMATO", 0) > 0:
        # Find unplanted empty tiles
        available = [t for t in tiles["empty"] if t not in ts["planted"]]
        # Limit to reasonable number (max 15 plants)
        available = available[:max(0, 15 - len(ts["planted"]))]

        for px, py in available:
            if not pass_units:
                break

            best_i, best_d = -1, 999
            for i in pass_units:
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                d = _dist(pos_i, (px, py))
                if d < best_d:
                    best_d = d
                    best_i = i

            if best_i >= 0:
                pos_i = _pos(farm, best_i)

                # Check if this unit is already on a planting mission
                if best_i in ts["targets"]:
                    target = ts["targets"][best_i]
                    if _adj_shed(pos_i) and best_i not in ts["has_seed"]:
                        # Pick up seed
                        if seeds.get("TOMATO", 0) > 0:
                            all_acts[best_i] = ["PICKUP", "TOMATO", 1]
                            ts["has_seed"].add(best_i)
                            pass_units.remove(best_i)
                            continue
                    if pos_i == target:
                        all_acts[best_i] = ["PLANT", "TOMATO"]
                        ts["planted"].add(target)
                        ts["targets"].pop(best_i, None)
                        ts["has_seed"].discard(best_i)
                        pass_units.remove(best_i)
                        continue
                    else:
                        move = _move_to(pos_i, target)
                        if move:
                            all_acts[best_i] = move
                            pass_units.remove(best_i)
                            continue

                # Start new planting mission
                if _adj_shed(pos_i) and seeds.get("TOMATO", 0) > 0:
                    all_acts[best_i] = ["PICKUP", "TOMATO", 1]
                    ts["targets"][best_i] = (px, py)
                    ts["has_seed"].add(best_i)
                    ts["planted"].add((px, py))
                    pass_units.remove(best_i)
                else:
                    # Move toward shed
                    move = _move_to(pos_i, (5, 5))
                    if move:
                        all_acts[best_i] = move
                        pass_units.remove(best_i)

    # Reset planting state at start of each day
    if hour == 0:
        ts["targets"] = {}
        ts["has_seed"] = set()

    # Rebuild action dict
    return {
        "farmer": all_acts[0],
        "hands": all_acts[1:],
        "market": action.get("market", []),
    }

def _adj_shed(pos):
    return pos in SHED

# ============================================================
# Main agent
# ============================================================
def agent(observation, configuration=None):
    # Get base action from V43+C9
    action = _V43C9(observation, configuration)

    # On day 0, don't modify (let opening play out)
    day = observation["step"] // 24
    if day == 0:
        return action

    # Apply tomato layer
    try:
        return _tomato_layer(observation, action)
    except Exception:
        return action

# ============================================================
# Self-test
# ============================================================
if __name__ == "__main__":
    from kaggle_environments import make
    scores = []
    for seed in [0, 1, 2, 3, 5, 7, 42, 100, 1000, 9999]:
        _TSTATE.clear()
        env = make("kaggriculture", debug=True, configuration={
            "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
            "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1, "seed": seed,
        })
        trainer = env.train([None, "random"])
        obs = trainer.reset()
        done = False
        while not done:
            obs_json = json.loads(json.dumps(obs))
            action = agent(obs_json)
            obs, reward, done, info = trainer.step(action)
        scores.append(reward)
        print(f"Seed {seed:5d}: ${reward:,.0f}")

    print(f"\nHybrid Mean: ${sum(scores)/len(scores):,.0f}")
    print(f"Min:  ${min(scores):,.0f}")
    print(f"Max:  ${max(scores):,.0f}")

    # Compare with V43+C9 baseline
    base_scores = []
    for seed in [0, 1, 2, 3, 5, 7, 42, 100, 1000, 9999]:
        env = make("kaggriculture", debug=True, configuration={
            "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
            "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
            "farmHandCostMult": 1, "seed": seed,
        })
        trainer = env.train([None, "random"])
        obs = trainer.reset()
        done = False
        while not done:
            obs_json = json.loads(json.dumps(obs))
            action = _V43C9(obs_json)
            obs, reward, done, info = trainer.step(action)
        base_scores.append(reward)

    print(f"\nV43+C9 Mean: ${sum(base_scores)/len(base_scores):,.0f}")
    print(f"Min:  ${min(base_scores):,.0f}")
    print(f"Max:  ${max(base_scores):,.0f}")

    diff = sum(scores) - sum(base_scores)
    print(f"\nDifference: ${diff:+,.0f} total (${diff/len(scores):+,.0f} avg)")
