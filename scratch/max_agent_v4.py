"""Simple maximized COW+SHEEP+TOMATO agent - v4.

Key insight: each unit does ONE action per step. Need step-by-step planning.

Day 0 plan (24 steps):
  Step 0: Market: BUY_LAND, BUY_ANIMAL COW x2, BUY_ANIMAL SHEEP x2, HIRE x5
  Steps 1-6: Build 4 PASTUREs (farmer + hands, each moves then builds)
  Steps 7-10: Place 4 animals (COW x2, SHEEP x2) on structures
  Step 11: Market: BUY_SEED TOMATO x15, BUY_PRODUCT WHEAT x10
  Steps 12-23: Move to empty tiles, pick up seeds, start planting

Day 1+ plan (24 steps per day):
  Step 0: Market: sell products, buy WHEAT for feed, buy TOMATO seeds
  Steps 1-23: Feed animals, water plants, harvest, plant tomatoes
"""
import json

BOARD = 10
SHED = {(4,4),(5,4),(4,5),(5,5)}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
LAND_PRICES = [1000, 2000, 4000]
LAND_ORDER = ["NE", "SW", "SE"]

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
    """Single move toward target. Returns action list."""
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

def _adj_shed(pos):
    return pos in SHED

# ============================================================
# Board scan
# ============================================================
def _scan(farm, unlocked):
    animals = []
    need_feed = []
    fert = []
    unwatered = []
    harvest = []
    empty = []
    empty_structs = []

    for y in range(BOARD):
        for x in range(BOARD):
            if (x, y) in SHED:
                continue
            tile = farm["tiles"][y][x]
            if tile is None and _quad(x, y) in unlocked:
                empty.append((x, y))
            elif isinstance(tile, dict):
                kind = tile.get("kind", "")
                if "animal" in tile:
                    animals.append((x, y, tile))
                    if not tile.get("fed_today"):
                        need_feed.append((x, y, tile))
                    if tile.get("fertilizer_available"):
                        fert.append((x, y, tile))
                    if tile.get("yield_units", 0) > 0:
                        harvest.append((x, y, tile))
                elif kind == "PLANT":
                    if not tile.get("watered_today"):
                        unwatered.append((x, y, tile))
                    if tile.get("yield_units", 0) > 0:
                        harvest.append((x, y, tile))
                elif kind in ("COOP", "PASTURE") and "animal" not in tile:
                    empty_structs.append((x, y, kind))
    return {
        "animals": animals, "need_feed": need_feed, "fert": fert,
        "unwatered": unwatered, "harvest": harvest,
        "empty": empty, "empty_structs": empty_structs,
    }

# ============================================================
# Persistent state
# ============================================================
_PS = {}

def _get_ps(pid):
    if pid not in _PS:
        _PS[pid] = {
            # For each unit: {"goal": str, "target": (x,y), "phase": str}
            "unit_goals": {},
            "build_targets": [],  # list of (x,y) assigned to units for building
            "place_queue": [],    # animals waiting to be placed
            "plant_queue": [],    # (x,y) waiting to be planted
            "carrying_seed": set(), # units carrying tomato seeds
            "carrying_item": {},  # unit -> item name (for DROP)
        }
    return _PS[pid]

# ============================================================
# Agent
# ============================================================
def agent(observation, configuration=None):
    step = observation["step"]
    day = step // 24
    hour = step % 24
    farm = observation["farms"][observation["player"]]
    private = observation["private"]
    shed = private.get("shed", {})
    seeds = private.get("seeds", {})
    money = farm["money"]
    unlocked = farm["unlocked_quadrants"]
    hands = farm.get("hands", [])
    n_units = 1 + len(hands)

    ps = _get_ps(observation["player"])
    board = _scan(farm, unlocked)

    orders = []
    acts = [["PASS"] for _ in range(n_units)]

    # ============================================================
    # Helper: find nearest free unit to a target
    # ============================================================
    def _best_unit(targets, exclude=None):
        """For each target, find best free unit. Returns list of (unit_idx, target)."""
        exclude = exclude or set()
        assignments = []
        used = set(exclude)
        for t in targets:
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in used:
                    continue
                if acts[i] != ["PASS"]:
                    continue
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                d = _dist(pos_i, t)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                assignments.append((best_i, t))
                used.add(best_i)
        return assignments

    # ============================================================
    # DAY 0: Opening
    # ============================================================
    if day == 0:
        if hour == 0:
            # Buy land, animals, hire hands
            orders = [
                ["BUY_LAND"],
                ["BUY_ANIMAL", "COW", 2],
                ["BUY_ANIMAL", "SHEEP", 2],
                ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ]
            # Farmer PASS (hands don't exist yet)

        else:
            # Steps 1-23: Build structures, place animals, plant
            # Figure out what still needs doing
            
            # Need 4 structures (2 for COWs, 2 for SHEEPs)
            n_structs_needed = 4 - len(board["empty_structs"])
            # Animals in shed waiting to be placed
            shed_animals = []
            for a in ["COW", "COW", "SHEEP", "SHEEP"]:
                if shed.get(a, 0) > 0:
                    shed_animals.append(a)
            
            # Phase 1: Build structures if needed
            if n_structs_needed > 0:
                # Pick empty tiles to build on (near shed for efficiency)
                available = [t for t in board["empty"] 
                           if t not in ps["build_targets"]]
                available.sort(key=lambda t: _dist(t, (5, 5)))
                
                targets = available[:n_structs_needed]
                if targets:
                    ps["build_targets"] = targets
                    
                    # Assign units to move+build
                    for i in range(n_units):
                        if acts[i] != ["PASS"]:
                            continue
                        pos_i = _pos(farm, i)
                        if pos_i is None:
                            continue
                        # Find which target this unit should go to
                        for t in targets:
                            if pos_i == t:
                                acts[i] = ["BUILD_PASTURE"]
                                break
                        else:
                            # Move toward nearest target
                            if targets:
                                move = _move_to(pos_i, targets[0])
                                if move:
                                    acts[i] = move

            # Phase 2: Place animals on structures
            elif shed_animals and board["empty_structs"]:
                structs = board["empty_structs"]
                placed = 0
                for i in range(n_units):
                    if placed >= min(len(shed_animals), len(structs)):
                        break
                    if acts[i] != ["PASS"]:
                        continue
                    pos_i = _pos(farm, i)
                    if pos_i is None:
                        continue
                    target = (structs[placed][0], structs[placed][1])
                    animal = shed_animals[placed]
                    if pos_i == target:
                        acts[i] = ["PLACE", animal]
                        placed += 1
                    else:
                        move = _move_to(pos_i, target)
                        if move:
                            acts[i] = move

            # Phase 3: Buy seeds + wheat (once structures done, animals placed)
            elif hour == 3 or (hour > 3 and seeds.get("TOMATO", 0) == 0 and money > 200):
                if shed.get("COW", 0) == 0 and shed.get("SHEEP", 0) == 0:
                    # Animals already placed, buy seeds
                    orders = [
                        ["BUY_SEED", "TOMATO", 15],
                        ["BUY_PRODUCT", "WHEAT", 10],
                    ]
                    # Start moving farmer to first empty tile
                    if board["empty"]:
                        pos0 = _pos(farm, 0)
                        if pos0 and not _adj_shed(pos0):
                            move = _move_to(pos0, board["empty"][0])
                            if move:
                                acts[0] = move

            # Phase 4: Plant tomatoes
            else:
                empty_tiles = board["empty"]
                if empty_tiles and seeds.get("TOMATO", 0) > 0:
                    # Need: go to shed, PICKUP TOMATO, go to tile, PLANT TOMATO
                    for i in range(n_units):
                        if acts[i] != ["PASS"]:
                            continue
                        pos_i = _pos(farm, i)
                        if pos_i is None:
                            continue
                        
                        if i in ps.get("planting_target", {}):
                            # Already heading to a tile to plant
                            target = ps["planting_target"][i]
                            if _adj_shed(pos_i) and i not in ps.get("has_seed", set()):
                                acts[i] = ["PICKUP", "TOMATO", 1]
                                ps.setdefault("has_seed", set()).add(i)
                            elif pos_i == target:
                                acts[i] = ["PLANT", "TOMATO"]
                                ps.get("planting_target", {}).pop(i, None)
                                ps.get("has_seed", set()).discard(i)
                            else:
                                move = _move_to(pos_i, target)
                                if move:
                                    acts[i] = move
                        elif _adj_shed(pos_i):
                            # At shed, pick up seed
                            if seeds.get("TOMATO", 0) > 0:
                                # Find unclaimed tile
                                claimed = set(ps.get("planting_target", {}).values())
                                for t in empty_tiles:
                                    if t not in claimed:
                                        ps.setdefault("planting_target", {})[i] = t
                                        acts[i] = ["PICKUP", "TOMATO", 1]
                                        ps.setdefault("has_seed", set()).add(i)
                                        break
                        else:
                            # Move toward shed
                            move = _move_to(pos_i, (5, 5))
                            if move:
                                acts[i] = move

    # ============================================================
    # DAY 1+: Daily routine
    # ============================================================
    else:
        # Hour 0: Market orders
        if hour == 0:
            # Sell products
            for item in PRODUCTS:
                if item == "WHEAT" or item == "FERTILIZER":
                    continue
                if shed.get(item, 0) > 0:
                    orders.append(["SELL", item, shed[item]])

            # Buy wheat for feed
            n_animals = len(board["animals"])
            wheat_have = shed.get("WHEAT", 0)
            wheat_need = max(0, n_animals - wheat_have)
            if wheat_need > 0 and money > wheat_need * 25 + 500:
                orders.append(["BUY_PRODUCT", "WHEAT", min(wheat_need, 30)])

            # Buy tomato seeds
            n_empty = len(board["empty"])
            seeds_have = seeds.get("TOMATO", 0)
            if n_empty > seeds_have and money > 500:
                orders.append(["BUY_SEED", "TOMATO", min(n_empty - seeds_have, 20)])

            # Buy land if affordable
            n_ul = len(unlocked) - 1
            if n_ul < len(LAND_ORDER) and money > LAND_PRICES[n_ul] + 2000:
                orders.append(["BUY_LAND"])

            # Hire more hands if needed/affordable
            if n_units < 8 and money > 500:
                orders.append(["HIRE"])

            orders = orders[:10]

        # Steps 1-23: Farm work
        # Priority: feed > water > harvest > plant > fert > carry

        # 1. FEED un-fed animals
        for ax, ay, _ in board["need_feed"]:
            if all(acts[i] != ["PASS"] for i in range(n_units)):
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if acts[i] != ["PASS"]:
                    continue
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                d = _dist(pos_i, (ax, ay))
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos_i = _pos(farm, best_i)
                if pos_i == (ax, ay):
                    acts[best_i] = ["FEED"]
                else:
                    move = _move_to(pos_i, (ax, ay))
                    if move:
                        acts[best_i] = move

        # 2. WATER unwatered plants
        for wx, wy, _ in board["unwatered"]:
            if all(acts[i] != ["PASS"] for i in range(n_units)):
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if acts[i] != ["PASS"]:
                    continue
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
                    acts[best_i] = ["WATER"]
                else:
                    move = _move_to(pos_i, (wx, wy))
                    if move:
                        acts[best_i] = move

        # 3. HARVEST anything with yield
        for hx, hy, _ in board["harvest"]:
            if all(acts[i] != ["PASS"] for i in range(n_units)):
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if acts[i] != ["PASS"]:
                    continue
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
                    acts[best_i] = ["HARVEST"]
                else:
                    move = _move_to(pos_i, (hx, hy))
                    if move:
                        acts[best_i] = move

        # 4. PLANT tomatoes (if seeds available and before day 22)
        if seeds.get("TOMATO", 0) > 0 and day < 22:
            for px, py in board["empty"]:
                if all(acts[i] != ["PASS"] for i in range(n_units)):
                    break
                if (px, py) in ps.get("planted", set()):
                    continue
                # Find best free unit
                best_i, best_d = -1, 999
                for i in range(n_units):
                    if acts[i] != ["PASS"]:
                        continue
                    pos_i = _pos(farm, i)
                    if pos_i is None:
                        continue
                    d = _dist(pos_i, (px, py))
                    if d < best_d:
                        best_d = d
                        best_i = i
                if best_i >= 0:
                    pos_i = _pos(farm, best_i)
                    if _adj_shed(pos_i):
                        acts[best_i] = ["PICKUP", "TOMATO", 1]
                        ps.setdefault("to_plant", {})[best_i] = (px, py)
                        ps.setdefault("planted", set()).add((px, py))
                    elif best_i in ps.get("to_plant", {}):
                        target = ps["to_plant"][best_i]
                        if pos_i == target:
                            acts[best_i] = ["PLANT", "TOMATO"]
                            del ps["to_plant"][best_i]
                        else:
                            move = _move_to(pos_i, target)
                            if move:
                                acts[best_i] = move
                    else:
                        move = _move_to(pos_i, (5, 5))
                        if move:
                            acts[best_i] = move

        # 5. COLLECT FERTILIZER
        for fx, fy, _ in board["fert"]:
            if all(acts[i] != ["PASS"] for i in range(n_units)):
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if acts[i] != ["PASS"]:
                    continue
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                d = _dist(pos_i, (fx, fy))
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos_i = _pos(farm, best_i)
                if pos_i == (fx, fy):
                    acts[best_i] = ["COLLECT_FERTILIZER"]
                else:
                    move = _move_to(pos_i, (fx, fy))
                    if move:
                        acts[best_i] = move

        # 6. Free units: carry to shed and drop
        for i in range(n_units):
            if acts[i] != ["PASS"]:
                continue
            pos_i = _pos(farm, i)
            if pos_i is None:
                continue
            if _adj_shed(pos_i):
                acts[i] = ["DROP"]
            else:
                move = _move_to(pos_i, (5, 5))
                if move:
                    acts[i] = move

        # Reset planting state at start of each day
        if hour == 0:
            ps.pop("to_plant", None)
            ps.pop("planted", None)

    return {
        "farmer": acts[0],
        "hands": acts[1:] if len(acts) > 1 else [],
        "market": orders,
    }


# ============================================================
# Self-test
# ============================================================
if __name__ == "__main__":
    from kaggle_environments import make
    scores = []
    for seed in [0, 1, 2, 3, 5, 7, 42, 100, 1000, 9999]:
        _PS.clear()
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
    print(f"\nMean: ${sum(scores)/len(scores):,.0f}")
    print(f"Min:  ${min(scores):,.0f}")
    print(f"Max:  ${max(scores):,.0f}")
