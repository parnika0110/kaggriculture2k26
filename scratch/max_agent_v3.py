"""Maximized COW+SHEEP+TOMATO agent - v3.

CRITICAL: Each unit gets exactly ONE action per step (not a path).
The engine executes action[0] only; rest is discarded.

Strategy:
- Day 0 steps 0-23: Buy animals, build structures, place animals, buy seeds
- Day 1+ steps 0-23: Feed, water, harvest, plant, sell
"""
import json
import math

BOARD = 10
SHED = {(4,4),(5,4),(4,5),(5,5)}
CROPS = {
    "WHEAT": {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "TOMATO": {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP", "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW": {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
LAND_PRICES = [1000, 2000, 4000]
LAND_ORDER = ["NE", "SW", "SE"]
DIRS = {"NORTH": (0,-1), "SOUTH": (0,1), "EAST": (1,0), "WEST": (-1,0)}

def _quad(x, y):
    h = BOARD // 2
    return ("N" if y < h else "S") + ("W" if x < h else "E")

def _adj_shed(x, y):
    return (x, y) in SHED

def _pos(farm, idx):
    if idx == 0:
        return tuple(farm["farmer"])
    hands = farm.get("hands", [])
    if 0 <= idx - 1 < len(hands):
        return tuple(hands[idx - 1])
    return None

def _move_toward(pos, target):
    """Return single move action toward target."""
    x, y = pos
    tx, ty = target
    if x < tx: return "EAST"
    if x > tx: return "WEST"
    if y < ty: return "SOUTH"
    if y > ty: return "NORTH"
    return None  # already there

def _dist(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

# ============================================================
# Persistent state
# ============================================================
_PS = {}

def _s(pid):
    if pid not in _PS:
        _PS[pid] = {
            # Unit task assignment: unit_idx -> {"type": ..., "target": (x,y), "phase": ...}
            "tasks": {},
            # Which build slots we've claimed
            "build_claimed": set(),
            # Which empty tiles we've claimed for planting
            "plant_claimed": set(),
            # What each unit is carrying
            "carrying": {},
        }
    return _PS[pid]

def _scan(farm, unlocked):
    """Single pass board scan."""
    animals = []
    animals_need_feed = []
    animals_fert = []
    plants_unwatered = []
    plants_harvest = []
    empty = []
    empty_structs = []

    for y in range(BOARD):
        for x in range(BOARD):
            if (x, y) in SHED:
                continue
            tile = farm["tiles"][y][x]
            if tile is None:
                if _quad(x, y) in unlocked:
                    empty.append((x, y))
            elif tile == "LOCKED":
                pass
            elif isinstance(tile, dict):
                kind = tile.get("kind", "")
                if "animal" in tile:
                    animals.append((x, y, tile))
                    if not tile.get("fed_today"):
                        animals_need_feed.append((x, y, tile))
                    if tile.get("fertilizer_available"):
                        animals_fert.append((x, y, tile))
                    if tile.get("yield_units", 0) > 0:
                        plants_harvest.append((x, y, tile))
                elif kind == "PLANT":
                    if not tile.get("watered_today"):
                        plants_unwatered.append((x, y, tile))
                    if tile.get("yield_units", 0) > 0:
                        plants_harvest.append((x, y, tile))
                elif kind in ("COOP", "PASTURE") and "animal" not in tile:
                    empty_structs.append((x, y, kind))

    return {
        "animals": animals,
        "animals_need_feed": animals_need_feed,
        "animals_fert": animals_fert,
        "plants_unwatered": plants_unwatered,
        "plants_harvest": plants_harvest,
        "empty": empty,
        "empty_structs": empty_structs,
    }

# ============================================================
# Main agent
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

    st = _s(observation["player"])
    board = _scan(farm, unlocked)

    orders = []
    acts = ["PASS"] * n_units  # one action per unit

    # ============================================================
    # DAY 0: Setup
    # ============================================================
    if day == 0:
        if hour == 0:
            # Step 0: Buy land NE, 2 COW, 2 SHEEP, hire 5
            orders = [
                ["BUY_LAND"],
                ["BUY_ANIMAL", "COW", 2],
                ["BUY_ANIMAL", "SHEEP", 2],
                ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"],
            ]
        elif hour == 1:
            # Hands just appeared. Build PASTUREs on nearby empty tiles.
            # We need 4 pastures (2 cow + 2 sheep).
            # Pick empty tiles near shed for building.
            nearby_empty = sorted(
                [t for t in board["empty"] if _dist(t, (5, 5)) <= 4],
                key=lambda t: _dist(t, (5, 5))
            )
            # Claim tiles for building
            to_build = []
            for t in nearby_empty:
                if len(to_build) >= 4:
                    break
                if t not in st["build_claimed"]:
                    st["build_claimed"].add(t)
                    to_build.append(t)

            # Assign farmer + hands to build
            for i in range(min(n_units, len(to_build))):
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                target = to_build[i]
                if pos_i == target:
                    acts[i] = "BUILD_PASTURE"
                else:
                    move = _move_toward(pos_i, target)
                    if move:
                        acts[i] = move

        elif hour == 2:
            # Place animals from shed onto empty structures
            structs = board["empty_structs"]
            to_place = []
            for a in ["COW", "COW", "SHEEP", "SHEEP"]:
                if shed.get(a, 0) > 0:
                    to_place.append(a)

            placed = 0
            for i in range(n_units):
                if placed >= len(to_place) or placed >= len(structs):
                    break
                pos_i = _pos(farm, i)
                if pos_i is None:
                    continue
                target = (structs[placed][0], structs[placed][1])
                animal = to_place[placed]
                if pos_i == target:
                    acts[i] = "PLACE " + animal
                    placed += 1
                else:
                    move = _move_toward(pos_i, target)
                    if move:
                        acts[i] = move

            # Fix: PLACE needs to be a proper list
            for i in range(n_units):
                if acts[i].startswith("PLACE "):
                    animal = acts[i].split(" ", 1)[1]
                    acts[i] = ["PLACE", animal]
                else:
                    acts[i] = [acts[i]]

        elif hour == 3:
            # Buy tomato seeds and wheat
            orders = [
                ["BUY_SEED", "TOMATO", 15],
                ["BUY_PRODUCT", "WHEAT", 10],
            ]
            # Farmer: start moving toward first empty tile for planting
            if board["empty"]:
                target = board["empty"][0]
                pos0 = _pos(farm, 0)
                if pos0:
                    move = _move_toward(pos0, target)
                    if move:
                        acts[0] = [move]

        else:
            # Hours 4-23: continue building/placing if needed, or start planting
            # Check if we still need structures
            if len(board["empty_structs"]) < 4 and board["empty"]:
                # Build more structures
                nearby_empty = sorted(
                    [t for t in board["empty"] if _dist(t, (5, 5)) <= 6 and t not in st["build_claimed"]],
                    key=lambda t: _dist(t, (5, 5))
                )
                if nearby_empty:
                    target = nearby_empty[0]
                    st["build_claimed"].add(target)
                    for i in range(n_units):
                        if acts[i] != ["PASS"]:
                            continue
                        pos_i = _pos(farm, i)
                        if pos_i is None:
                            continue
                        if pos_i == target:
                            acts[i] = ["BUILD_PASTURE"]
                            break
                        else:
                            move = _move_toward(pos_i, target)
                            if move:
                                acts[i] = [move]
                                break

    # ============================================================
    # DAY 1+: Daily routine
    # ============================================================
    else:
        if hour == 0:
            # Sell products, buy wheat, buy seeds
            for item in PRODUCTS:
                if item == "WHEAT":
                    continue
                if shed.get(item, 0) > 0:
                    orders.append(["SELL", item, shed[item]])

            n_animals = len(board["animals"])
            wheat_have = shed.get("WHEAT", 0)
            wheat_need = max(0, n_animals - wheat_have)
            if wheat_need > 0 and money > wheat_need * 25 + 200:
                orders.append(["BUY_PRODUCT", "WHEAT", min(wheat_need, 30)])

            n_empty = len(board["empty"])
            seeds_have = seeds.get("TOMATO", 0)
            if n_empty > seeds_have and money > 500:
                orders.append(["BUY_SEED", "TOMATO", min(n_empty - seeds_have, 20)])

            # Buy land if affordable
            n_ul = len(unlocked) - 1
            if n_ul < len(LAND_ORDER) and money > LAND_PRICES[n_ul] + 2000:
                orders.append(["BUY_LAND"])

            orders = orders[:10]

        # ============================================================
        # ASSIGN TASKS: One action per unit per step
        # ============================================================
        # Priority: feed > water > harvest > plant > fert > carry

        assigned = set()

        # 1. FEED: Find un-fed animals, assign units to feed them
        for ax, ay, _ in board["animals_need_feed"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
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
                    move = _move_toward(pos_i, (ax, ay))
                    if move:
                        acts[best_i] = [move]
                assigned.add(best_i)

        # 2. WATER unwatered plants
        for wx, wy, _ in board["plants_unwatered"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
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
                    move = _move_toward(pos_i, (wx, wy))
                    if move:
                        acts[best_i] = [move]
                assigned.add(best_i)

        # 3. HARVEST anything with yield
        for hx, hy, _ in board["plants_harvest"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
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
                    move = _move_toward(pos_i, (hx, hy))
                    if move:
                        acts[best_i] = [move]
                assigned.add(best_i)

        # 4. PLANT tomatoes (only before day 22, need seeds)
        if seeds.get("TOMATO", 0) > 0 and day < 22:
            for px, py in board["empty"]:
                if len(assigned) >= n_units:
                    break
                if (px, py) in st["plant_claimed"]:
                    continue
                best_i, best_d = -1, 999
                for i in range(n_units):
                    if i in assigned:
                        continue
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
                    # Need to pick up seed from shed first
                    shed_pos = (5, 5)  # nearest shed access
                    if _adj_shed(pos_i[0], pos_i[1]) and private.get("seeds", {}).get("TOMATO", 0) > 0:
                        # At shed, pick up seed
                        acts[best_i] = ["PICKUP", "TOMATO", 1]
                        st["carrying"][best_i] = ("TOMATO_SEED", (px, py))
                        st["plant_claimed"].add((px, py))
                    elif best_i in st["carrying"] and st["carrying"][best_i][0] == "TOMATO_SEED":
                        # Carrying seed, move to target or plant
                        target = st["carrying"][best_i][1]
                        if pos_i == target:
                            acts[best_i] = ["PLANT", "TOMATO"]
                            del st["carrying"][best_i]
                        else:
                            move = _move_toward(pos_i, target)
                            if move:
                                acts[best_i] = [move]
                    else:
                        # Go to shed to pick up seed
                        if pos_i in SHED:
                            acts[best_i] = ["PICKUP", "TOMATO", 1]
                            st["carrying"][best_i] = ("TOMATO_SEED", (px, py))
                            st["plant_claimed"].add((px, py))
                        else:
                            move = _move_toward(pos_i, (5, 5))
                            if move:
                                acts[best_i] = [move]
                    assigned.add(best_i)

        # 5. COLLECT FERTILIZER
        for fx, fy, _ in board["animals_fert"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
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
                    move = _move_toward(pos_i, (fx, fy))
                    if move:
                        acts[best_i] = [move]
                assigned.add(best_i)

        # 6. Free units: carry to shed and drop, or move toward shed
        for i in range(n_units):
            if i in assigned:
                continue
            if acts[i] != ["PASS"]:
                continue
            pos_i = _pos(farm, i)
            if pos_i is None:
                continue
            # Check if carrying something
            if i in st["carrying"]:
                target = st["carrying"][i][1]
                move = _move_toward(pos_i, target)
                if move:
                    acts[i] = [move]
                continue
            if _adj_shed(pos_i[0], pos_i[1]):
                acts[i] = ["DROP"]
            else:
                move = _move_toward(pos_i, (5, 5))
                if move:
                    acts[i] = [move]

    # Convert any bare strings to lists
    for i in range(n_units):
        if isinstance(acts[i], str):
            acts[i] = [acts[i]]

    return {
        "farmer": acts[0] if isinstance(acts[0], list) else [acts[0]],
        "hands": [a if isinstance(a, list) else [a] for a in acts[1:]],
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
