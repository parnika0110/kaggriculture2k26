"""Maximized COW+SHEEP+TOMATO agent.

Strategy:
- Days 0-1: Buy land, animals, structures, hire hands
- Days 2-7: Plant tomatoes on available tiles, water daily
- Days 8+: Harvest tomatoes + animals, sell at market
- Always: feed animals, care for animals, buy wheat as needed
"""
import json
import math
import copy

# ============================================================
# Constants from the game engine
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

MARKET_I0 = 10000
PRICE_FLOOR = 1

MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": MARKET_I0, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": MARKET_I0, "T": 450, "below_func": "log",    "below_target": 0.20, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": MARKET_I0, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": MARKET_I0, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": MARKET_I0, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": MARKET_I0, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": MARKET_I0, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

FARMER_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}

SHOPS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}

LAND_ORDER = ["NE", "SW", "SE"]
LAND_PRICES = [1000, 2000, 4000]

# ============================================================
# Market price function (replicated from engine)
# ============================================================
def _shape(func, x):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq":     return x * x
    if func == "sqrt":   return math.sqrt(x)
    if func == "log":    return math.log(1.0 + x)
    if func == "log10":  return math.log10(1.0 + x)
    return x

def market_price(item, inventory):
    p = MARKET_PARAMS[item]
    base, I0, T = p["base"], p["I0"], p["T"]
    if inventory < I0:
        amp = p["below_target"] * base / _shape(p["below_func"], T)
        price = base + amp * _shape(p["below_func"], I0 - inventory)
    else:
        amp = p["above_target"] * base / _shape(p["above_func"], T)
        price = base - amp * _shape(p["above_func"], inventory - I0)
    return max(PRICE_FLOOR, int(round(price)))

# ============================================================
# Pathfinding
# ============================================================
def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _walk_path(pos, target):
    """Simple manhattan path from pos to target."""
    path = []
    x, y = pos
    tx, ty = target
    while x < tx: path.append("EAST"); x += 1
    while x > tx: path.append("WEST"); x -= 1
    while y < ty: path.append("SOUTH"); y += 1
    while y > ty: path.append("NORTH"); y -= 1
    return path

SHED_TILES = [(4,4), (5,4), (4,5), (5,5)]
BOARD_SIZE = 10

def _is_shed_adjacent(pos):
    return tuple(pos) in set(SHED_TILES)

def _quadrant(x, y):
    half = BOARD_SIZE // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")

# ============================================================
# State tracking (persisted across turns via closure)
# ============================================================
_STATE = {}

def _get_state(player):
    if player not in _STATE:
        _STATE[player] = {
            "phase": "setup",      # setup -> planting -> harvest
            "target_animals": [],  # list of (animal_type, structure_type)
            "planted_tiles": set(),
            "all_empty_tiles": [],
            "day_planned": -1,
            "hands_hired_today": 0,
        }
    return _STATE[player]

def _find_empty_tiles(farm, unlocked):
    """Find all empty tiles in unlocked quadrants, excluding shed access."""
    empty = []
    shed_set = set(SHED_TILES)
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            if (x, y) in shed_set:
                continue
            tile = farm["tiles"][y][x]
            if tile is None and _quadrant(x, y) in unlocked:
                empty.append((x, y))
    return empty

def _find_structures(farm, kind):
    """Find all tiles with a given structure kind (COOP/PASTURE) that have no animal."""
    result = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == kind and "animal" not in tile:
                result.append((x, y))
    return result

def _find_animals(farm, animal_type=None):
    """Find all tiles with animals, optionally filtered by type."""
    result = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and "animal" in tile:
                if animal_type is None or tile["animal"] == animal_type:
                    result.append((x, y, tile))
    return result

def _find_plants(farm, crop=None, with_yield=False):
    """Find all plant tiles, optionally filtered by crop and yield."""
    result = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                if crop and tile.get("crop") != crop:
                    continue
                if with_yield and tile.get("yield_units", 0) <= 0:
                    continue
                result.append((x, y, tile))
    return result

def _find_unwatered_plants(farm):
    """Find plants that need watering today."""
    result = []
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today"):
                result.append((x, y, tile))
    return result

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
    market = observation.get("market", {})
    prices = market.get("prices", {})
    money = farm["money"]
    unlocked = farm["unlocked_quadrants"]
    farmer_pos = farm["farmer"]
    hands = farm.get("hands", [])
    n_hands = len(hands)
    total_units = 1 + n_hands  # farmer + hands

    state = _get_state(observation["player"])

    # ---- Market orders ----
    orders = []
    farmer_action = ["PASS"]
    hands_actions = [[] for _ in range(n_hands)]

    # ============================================================
    # PHASE 0: Day 0 opening — buy land, animals, seeds, hire
    # ============================================================
    if day == 0 and hour == 0:
        # Budget: $3,000
        # Priority: land NE ($1000), 2 COW ($800), 2 SHEEP ($1000), seeds, hires
        orders = [
            ["BUY_LAND"],                           # $1000
            ["BUY_ANIMAL", "COW", 2],               # $800
            ["BUY_ANIMAL", "SHEEP", 2],             # $1000
        ]
        # That's $2800. We have $200 left.
        # No seeds/hires this turn — buy on day 1 after selling early goods

    elif day == 0 and hour == 1:
        # Build structures for animals we just bought
        # Farmer builds COOP or PASTURE at a strategic position
        # Hands place animals on structures
        pass  # Will handle below in unit actions

    elif day == 0 and hour == 2:
        orders = [["BUY_SEED", "TOMATO", 10], ["BUY_PRODUCT", "WHEAT", 5]]

    elif day == 1 and hour == 0:
        # Sell any products, buy more seeds and wheat
        shed_products = {k: v for k, v in shed.items() if k in PRODUCTS and v > 0}
        for item, qty in shed_products.items():
            orders.append(["SELL", item, qty])
        orders.append(["BUY_SEED", "TOMATO", 15])
        orders.append(["BUY_PRODUCT", "WHEAT", 10])
        # Hire hands
        for _ in range(5):
            orders.append(["HIRE"])

    elif day >= 1 and hour == 0:
        # Daily: sell products, buy wheat for feed, hire if needed
        for item in PRODUCTS:
            if shed.get(item, 0) > 0 and item != "WHEAT":
                orders.append(["SELL", item, shed[item]])

        # Count animals needing feed
        n_animals = len(_find_animals(farm))
        wheat_needed = max(0, n_animals - shed.get("WHEAT", 0))
        if wheat_needed > 0 and money > wheat_needed * 25:
            orders.append(["BUY_PRODUCT", "WHEAT", min(wheat_needed, 30)])

        # Buy tomato seeds if we have empty tiles and money
        empty_tiles = _find_empty_tiles(farm, unlocked)
        tomato_seeds_needed = min(len(empty_tiles), 30)
        current_seeds = seeds.get("TOMATO", 0)
        if tomato_seeds_needed > current_seeds and money > 500:
            to_buy = min(tomato_seeds_needed - current_seeds, 20)
            orders.append(["BUY_SEED", "TOMATO", to_buy])

        # Hire hands if we can afford it and need more labor
        if n_hands < 8 and money > 200:
            orders.append(["HIRE"])

    # Limit to 10 market orders
    orders = orders[:10]

    # ============================================================
    # UNIT ACTIONS: Farmer + Hands
    # ============================================================
    my_actions = [None] * total_units  # None = PASS

    # Determine what each unit should do based on priorities

    # Priority 1: Feed animals (CRITICAL - animals escape if unfed 2 days)
    animals = _find_animals(farm)
    unfed_animals = [(x, y, t) for x, y, t in animals if not t.get("fed_today")]
    need_wheat = []
    for i, (ax, ay, atile) in enumerate(unfed_animals):
        if i >= total_units:
            break
        # Check if this unit has wheat
        # For simplicity, assign units to feed animals
        need_wheat.append((ax, ay, i))

    # Priority 2: Water unwatered plants
    unwatered = _find_unwatered_plants(farm)

    # Priority 3: Harvest anything with yield
    harvestable = _find_plants(farm, with_yield=True)
    animal_harvest = [(x, y, t) for x, y, t in animals if t.get("yield_units", 0) > 0]
    harvestable.extend(animal_harvest)

    # Priority 4: Plant tomatoes on empty tiles
    empty_tiles = _find_empty_tiles(farm, unlocked)
    empty_tiles = [(x, y) for x, y in empty_tiles if (x, y) not in state["planted_tiles"]]
    can_plant = seeds.get("TOMATO", 0) > 0

    # Priority 5: Collect fertilizer from animals
    fert_animals = [(x, y, t) for x, y, t in animals if t.get("fertilizer_available")]

    # ============================================================
    # Simple reactive assignment
    # ============================================================
    unit_idx = 0  # 0 = farmer, 1+ = hands

    # Helper: assign a task to the next available unit
    def assign_task(task_func, start_idx=0):
        nonlocal unit_idx
        for i in range(start_idx, total_units):
            if my_actions[i] is None:
                result = task_func(i)
                if result is not None:
                    my_actions[i] = result
                    return True
        return False

    def unit_pos(idx):
        if idx == 0:
            return tuple(farmer_pos)
        if idx - 1 < len(hands):
            return tuple(hands[idx - 1])
        return None

    # --- Step 0: Build structures for animals we bought ---
    if day == 0 and hour == 1:
        # Build PASTUREs and COOPs on empty tiles near shed
        structures_to_build = []
        n_cows_sheep = shed.get("COW", 0) + shed.get("SHEEP", 0)
        n_geese = shed.get("GOOSE", 0)
        # Count existing structures
        existing_pastures = len(_find_structures(farm, "PASTURE"))
        existing_coops = len(_find_structures(farm, "COOP"))
        need_pastures = max(0, n_cows_sheep - existing_pastures)
        need_coops = max(0, n_geese - existing_coops)

        empty_near_shed = [t for t in empty_tiles if _manhattan(t, (5, 5)) <= 6]

        built = 0
        for x, y in empty_near_shed:
            if need_pastures > 0:
                structures_to_build.append((x, y, "BUILD_PASTURE"))
                need_pastures -= 1
                built += 1
            elif need_coops > 0:
                structures_to_build.append((x, y, "BUILD_COOP"))
                need_coops -= 1
                built += 1
            if built >= 5:  # Max 5 builds per step (farmer + 4 hands)
                break

        for i, (x, y, build_action) in enumerate(structures_to_build):
            if i < total_units:
                pos = unit_pos(i)
                if pos:
                    path = _walk_path(pos, (x, y))
                    if len(path) <= 23:  # Must complete in one step
                        my_actions[i] = path + [build_action]

    # --- Step 2+: Place animals ---
    elif day == 0 and hour >= 2 and hour <= 10:
        # Place animals from shed onto structures
        animals_in_shed = []
        for animal_type in ["GOOSE", "COW", "SHEEP"]:
            count = shed.get(animal_type, 0)
            for _ in range(count):
                animals_in_shed.append(animal_type)

        if animals_in_shed:
            # Find empty COOPs for geese, empty PASTUREs for cows/sheep
            empty_coops = _find_structures(farm, "COOP")
            empty_pastures = _find_structures(farm, "PASTURE")

            placed = 0
            for i in range(total_units):
                if my_actions[i] is not None:
                    continue
                if placed >= len(animals_in_shed):
                    break

                animal = animals_in_shed[placed]
                structure_needed = ANIMALS[animal]["structure"]
                if structure_needed == "COOP":
                    targets = empty_coops
                else:
                    targets = empty_pastures

                if targets:
                    target = targets[0]
                    targets.pop(0)
                    pos = unit_pos(i)
                    if pos:
                        path = _walk_path(pos, target)
                        if len(path) <= 22:
                            my_actions[i] = path + ["PLACE", animal]
                            placed += 1

    # --- Normal day actions (day >= 1) ---
    else:
        # Step 1: Assign feeding
        fed_count = 0
        for ax, ay, atile in unfed_animals:
            if fed_count >= total_units:
                break
            # Find best unit to feed this animal
            best_unit = -1
            best_dist = 999
            for i in range(total_units):
                if my_actions[i] is not None:
                    continue
                pos = unit_pos(i)
                if pos is None:
                    continue
                # Check if unit has wheat
                dist = _manhattan(pos, (ax, ay))
                if dist < best_dist:
                    best_dist = dist
                    best_unit = i

            if best_unit >= 0:
                pos = unit_pos(best_unit)
                path = _walk_path(pos, (ax, ay))
                # Need to pick up wheat from shed first if not carrying it
                # For simplicity, go to shed, pick up wheat, go to animal, feed
                shed_path = _walk_path(pos, (5, 5))
                to_animal = _walk_path((5, 5), (ax, ay))
                total_path = shed_path + ["PICKUP", "WHEAT", 1] + to_animal + ["FEED"]
                if len(total_path) <= 23:
                    my_actions[best_unit] = total_path
                    fed_count += 1

        # Step 2: Assign watering
        watered_count = 0
        for wx, wy, wtile in unwatered:
            if watered_count >= total_units:
                break
            best_unit = -1
            best_dist = 999
            for i in range(total_units):
                if my_actions[i] is not None:
                    continue
                pos = unit_pos(i)
                if pos is None:
                    continue
                dist = _manhattan(pos, (wx, wy))
                if dist < best_dist:
                    best_dist = dist
                    best_unit = i

            if best_unit >= 0:
                pos = unit_pos(best_unit)
                path = _walk_path(pos, (wx, wy))
                if len(path) <= 22:
                    my_actions[best_unit] = path + ["WATER"]
                    watered_count += 1

        # Step 3: Assign harvesting
        harvest_count = 0
        for hx, hy, htile in harvestable:
            if harvest_count >= total_units:
                break
            best_unit = -1
            best_dist = 999
            for i in range(total_units):
                if my_actions[i] is not None:
                    continue
                pos = unit_pos(i)
                if pos is None:
                    continue
                dist = _manhattan(pos, (hx, hy))
                if dist < best_dist:
                    best_dist = dist
                    best_unit = i

            if best_unit >= 0:
                pos = unit_pos(best_unit)
                path = _walk_path(pos, (hx, hy))
                if len(path) <= 22:
                    my_actions[best_unit] = path + ["HARVEST"]
                    harvest_count += 1

        # Step 4: Plant tomatoes on empty tiles
        if can_plant:
            plant_count = 0
            for px, py in empty_tiles:
                if plant_count >= total_units:
                    break
                best_unit = -1
                best_dist = 999
                for i in range(total_units):
                    if my_actions[i] is not None:
                        continue
                    pos = unit_pos(i)
                    if pos is None:
                        continue
                    dist = _manhattan(pos, (px, py))
                    if dist < best_dist:
                        best_dist = dist
                        best_unit = i

                if best_unit >= 0:
                    pos = unit_pos(best_unit)
                    # Pick up seed from shed, walk to tile, plant
                    shed_path = _walk_path(pos, (5, 5))
                    to_tile = _walk_path((5, 5), (px, py))
                    total_path = shed_path + ["PICKUP", "TOMATO", 1] + to_tile + ["PLANT", "TOMATO"]
                    if len(total_path) <= 22:
                        my_actions[best_unit] = total_path
                        state["planted_tiles"].add((px, py))
                        plant_count += 1

        # Step 5: Collect fertilizer
        fert_count = 0
        for fx, fy, ftile in fert_animals:
            if fert_count >= total_units:
                break
            best_unit = -1
            best_dist = 999
            for i in range(total_units):
                if my_actions[i] is not None:
                    continue
                pos = unit_pos(i)
                if pos is None:
                    continue
                dist = _manhattan(pos, (fx, fy))
                if dist < best_dist:
                    best_dist = dist
                    best_unit = i

            if best_unit >= 0:
                pos = unit_pos(best_unit)
                path = _walk_path(pos, (fx, fy))
                if len(path) <= 22:
                    my_actions[best_unit] = path + ["COLLECT_FERTILIZER"]
                    fert_count += 1

        # Step 6: Carry items to shed
        # Units that are free and near shed can drop off
        for i in range(total_units):
            if my_actions[i] is not None:
                continue
            pos = unit_pos(i)
            if pos is None:
                continue
            if _is_shed_adjacent(pos):
                my_actions[i] = ["DROP"]
            else:
                # Walk toward shed
                path = _walk_path(pos, (5, 5))
                if path:
                    my_actions[i] = path[:23]

    # Convert None to ["PASS"]
    for i in range(total_units):
        if my_actions[i] is None:
            my_actions[i] = ["PASS"]

    farmer_action = my_actions[0]
    hands_actions = my_actions[1:]

    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": orders,
    }


if __name__ == "__main__":
    from kaggle_environments import make
    import json as _json

    env = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": 0,
    })
    trainer = env.train([None, "random"])
    obs = trainer.reset()
    done = False
    total_steps = 0
    while not done:
        obs_json = _json.loads(_json.dumps(obs))
        action = agent(obs_json)
        obs, reward, done, info = trainer.step(action)
        total_steps += 1
    print(f"Score: ${reward:,.0f} in {total_steps} steps")
    print(f"Final money: ${obs['farms'][0]['money']:,.0f}")
