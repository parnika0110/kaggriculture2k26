"""Maximized COW+SHEEP+TOMATO agent - v2 (simplified, robust).

Key insight from V43+C9 analysis: it produces 17-19 animals but ZERO crops.
57 empty tiles are completely wasted. Adding tomatoes should yield +$50K+.

This agent focuses on:
1. Efficient animal setup (copy V43+C9's opening)
2. Tomato planting on ALL empty tiles
3. Daily watering/harvesting
4. Smart market sales
"""
import json
import math

# ============================================================
# Engine constants (replicated for self-containment)
# ============================================================
CROPS = {
    "WHEAT":      {"seed": 10, "first_yield_day": 2, "max_yield_day": 4, "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20, "first_yield_day": 2, "max_yield_day": 3, "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50, "first_yield_day": 8, "max_yield_day": 8, "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"seed": 100, "first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"seed": 80, "first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "structure": "COOP",    "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG"},
    "COW":   {"cost": 400, "structure": "PASTURE", "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK"},
    "SHEEP": {"cost": 500, "structure": "PASTURE", "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL"},
}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]
SHOPS = {
    "BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"], "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
BOARD = 10
SHED = [(4,4),(5,4),(4,5),(5,5)]

# ============================================================
# Path helpers
# ============================================================
def _path(pos, target):
    path = []
    x, y = pos
    tx, ty = target
    while x < tx: path.append("EAST"); x += 1
    while x > tx: path.append("WEST"); x -= 1
    while y < ty: path.append("SOUTH"); y += 1
    while y > ty: path.append("NORTH"); y -= 1
    return path

def _adj_shed(pos):
    return tuple(pos) in set(SHED)

def _quad(x, y):
    h = BOARD // 2
    return ("N" if y < h else "S") + ("W" if x < h else "E")

# ============================================================
# Tile scanners (fast — early exit when possible)
# ============================================================
def _scan_board(farm, unlocked):
    """Single pass: find empty tiles, structures, animals, plants."""
    empty = []
    struct_empty = []  # (x, y, kind)
    animals = []       # (x, y, tile_dict)
    animals_need_feed = []
    animals_fert = []
    plants_unwatered = []
    plants_harvest = []
    shed_set = set(SHED)

    for y in range(BOARD):
        for x in range(BOARD):
            if (x, y) in shed_set:
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
                    struct_empty.append((x, y, kind))
                elif kind == "WEED":
                    pass

    return {
        "empty": empty,
        "struct_empty": struct_empty,
        "animals": animals,
        "animals_need_feed": animals_need_feed,
        "animals_fert": animals_fert,
        "plants_unwatered": plants_unwatered,
        "plants_harvest": plants_harvest,
    }

# ============================================================
# Agent state (persists across turns)
# ============================================================
_PSTATE = {}

def _ps(player):
    if player not in _PSTATE:
        _PSTATE[player] = {
            "day0_hour0_done": False,
            "structures_built": 0,
            "animals_placed": set(),
            "seeds_planted": set(),
        }
    return _PSTATE[player]

def _unit_pos(farm, idx):
    if idx == 0:
        return tuple(farm["farmer"])
    hands = farm.get("hands", [])
    if idx - 1 < len(hands):
        return tuple(hands[idx - 1])
    return None

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

    ps = _ps(observation["player"])
    board = _scan_board(farm, unlocked)

    orders = []
    farmer_act = ["PASS"]
    hands_act = [["PASS"] for _ in range(len(hands))]

    def _all_acts():
        return [farmer_act] + hands_act

    def _set_act(idx, act):
        nonlocal farmer_act, hands_act
        if idx == 0:
            farmer_act = act
        else:
            hands_act[idx - 1] = act

    def _find_unit(max_dist=99, exclude=None):
        """Find the closest free unit to do work."""
        exclude = exclude or set()
        best_i, best_d = -1, 999
        for i in range(n_units):
            if i in exclude:
                continue
            acts = _all_acts()
            if acts[i] != ["PASS"]:
                continue
            pos = _unit_pos(farm, i)
            if pos is None:
                continue
            return i
        return -1

    # ============================================================
    # DAY 0: Opening
    # ============================================================
    if day == 0:
        if hour == 0:
            # Buy animals + hire hands (10 order limit)
            # Budget: $3000
            # Strategy: 2 COW + 2 SHEEP + land NE + 5 hires
            orders = [
                ["BUY_LAND"],              # $1000
                ["BUY_ANIMAL", "COW", 2],  # $800
                ["BUY_ANIMAL", "SHEEP", 2],# $1000
                ["HIRE"],                  # $1
                ["HIRE"],                  # $1
                ["HIRE"],                  # $2
                ["HIRE"],                  # $3
                ["HIRE"],                  # $5
            ]
            # Cost: $2812, remaining: $188

        elif hour == 1:
            # Hands now exist! Build PASTUREs for animals
            empty_near = [t for t in board["empty"]
                         if _path((5,5), t).__len__() <= 5]
            built = 0
            for i in range(n_units):
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                if built >= 4:  # Need 4 pastures (2 cow + 2 sheep)
                    break
                if built >= len(empty_near):
                    break
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                target = empty_near[built]
                p = _path(pos, target)
                if len(p) <= 22:
                    _set_act(i, p + ["BUILD_PASTURE"])
                    built += 1

        elif hour == 2:
            # Place animals from shed onto structures
            structs = board["struct_empty"]
            to_place = []
            for a in ["COW", "COW", "SHEEP", "SHEEP"]:
                if shed.get(a, 0) > 0:
                    to_place.append(a)

            placed = 0
            for i in range(n_units):
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                if placed >= len(to_place):
                    break
                if placed >= len(structs):
                    break
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                animal = to_place[placed]
                struct = structs[placed]
                target = (struct[0], struct[1])
                p = _path(pos, target)
                if len(p) <= 22:
                    _set_act(i, p + ["PLACE", animal])
                    placed += 1

        elif hour == 3:
            # Buy seeds and wheat for tomorrow
            orders = [
                ["BUY_SEED", "TOMATO", 20],
                ["BUY_PRODUCT", "WHEAT", 10],
            ]

    # ============================================================
    # DAY 1+: Daily routine
    # ============================================================
    elif day >= 1:
        if hour == 0:
            # Sell all products in shed (except wheat we need for feed)
            for item in PRODUCTS:
                if item == "WHEAT":
                    continue
                if shed.get(item, 0) > 0:
                    orders.append(["SELL", item, shed[item]])

            # Buy wheat for animal feed
            n_animals = len(board["animals"])
            wheat_have = shed.get("WHEAT", 0)
            wheat_need = max(0, n_animals - wheat_have)
            if wheat_need > 0 and money > wheat_need * 25 + 500:
                orders.append(["BUY_PRODUCT", "WHEAT", min(wheat_need, 30)])

            # Buy tomato seeds if we have empty tiles
            n_empty = len(board["empty"])
            seeds_have = seeds.get("TOMATO", 0)
            if n_empty > seeds_have and money > 1000:
                to_buy = min(n_empty - seeds_have, 20)
                orders.append(["BUY_SEED", "TOMATO", to_buy])

            # Buy land if we can afford it
            n_unlocked = len(unlocked) - 1  # NW always unlocked
            if n_unlocked < len(LAND_ORDER):
                land_cost = LAND_PRICES[n_unlocked]
                if money > land_cost + 1000:
                    orders.append(["BUY_LAND"])

            orders = orders[:10]

        # All hours: assign work to units
        # Priority: feed > water > harvest > plant > collect fert > carry to shed

        assigned = set()

        # 1. FEED animals (critical - escape after 2 days unfed)
        for ax, ay, atile in board["animals_need_feed"]:
            if len(assigned) >= n_units:
                break
            # Find closest free unit
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                d = abs(pos[0]-ax) + abs(pos[1]-ay)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos = _unit_pos(farm, best_i)
                # Go to shed, pick up wheat, go to animal, feed
                p = _path(pos, (5,5)) + ["PICKUP", "WHEAT", 1] + _path((5,5), (ax,ay)) + ["FEED"]
                if len(p) <= 23:
                    _set_act(best_i, p)
                    assigned.add(best_i)

        # 2. WATER unwatered plants
        for wx, wy, wtile in board["plants_unwatered"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                d = abs(pos[0]-wx) + abs(pos[1]-wy)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos = _unit_pos(farm, best_i)
                p = _path(pos, (wx, wy)) + ["WATER"]
                if len(p) <= 23:
                    _set_act(best_i, p)
                    assigned.add(best_i)

        # 3. HARVEST anything with yield
        for hx, hy, htile in board["plants_harvest"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                d = abs(pos[0]-hx) + abs(pos[1]-hy)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos = _unit_pos(farm, best_i)
                p = _path(pos, (hx, hy)) + ["HARVEST"]
                if len(p) <= 23:
                    _set_act(best_i, p)
                    assigned.add(best_i)

        # 4. PLANT tomatoes on empty tiles (only if we have seeds and it's early enough)
        if seeds.get("TOMATO", 0) > 0 and day < 22:  # Planting after day 22 won't yield
            for px, py in board["empty"]:
                if len(assigned) >= n_units:
                    break
                best_i, best_d = -1, 999
                for i in range(n_units):
                    if i in assigned:
                        continue
                    acts = _all_acts()
                    if acts[i] != ["PASS"]:
                        continue
                    pos = _unit_pos(farm, i)
                    if pos is None:
                        continue
                    d = abs(pos[0]-px) + abs(pos[1]-py)
                    if d < best_d:
                        best_d = d
                        best_i = i
                if best_i >= 0:
                    pos = _unit_pos(farm, best_i)
                    p = _path(pos, (5,5)) + ["PICKUP", "TOMATO", 1] + _path((5,5), (px,py)) + ["PLANT", "TOMATO"]
                    if len(p) <= 23:
                        _set_act(best_i, p)
                        assigned.add(best_i)

        # 5. COLLECT FERTILIZER from animals
        for fx, fy, ftile in board["animals_fert"]:
            if len(assigned) >= n_units:
                break
            best_i, best_d = -1, 999
            for i in range(n_units):
                if i in assigned:
                    continue
                acts = _all_acts()
                if acts[i] != ["PASS"]:
                    continue
                pos = _unit_pos(farm, i)
                if pos is None:
                    continue
                d = abs(pos[0]-fx) + abs(pos[1]-fy)
                if d < best_d:
                    best_d = d
                    best_i = i
            if best_i >= 0:
                pos = _unit_pos(farm, best_i)
                p = _path(pos, (fx, fy)) + ["COLLECT_FERTILIZER"]
                if len(p) <= 23:
                    _set_act(best_i, p)
                    assigned.add(best_i)

        # 6. Free units: carry to shed or wander near shed
        for i in range(n_units):
            if i in assigned:
                continue
            acts = _all_acts()
            if acts[i] != ["PASS"]:
                continue
            pos = _unit_pos(farm, i)
            if pos is None:
                continue
            if _adj_shed(pos):
                _set_act(i, ["DROP"])
            else:
                p = _path(pos, (5, 5))
                if p:
                    _set_act(i, p[:23])

    return {
        "farmer": farmer_act,
        "hands": hands_act,
        "market": orders,
    }


# ============================================================
# Self-test
# ============================================================
if __name__ == "__main__":
    from kaggle_environments import make
    scores = []
    for seed in [0, 1, 2, 3, 5, 7, 42, 100, 1000, 9999]:
        _PSTATE.clear()
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
