import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make

def cow_agent(obs, config=None):
    """
    Cow Livestock Strategy:
    1. Early game: Buy Wheat seeds, plant Wheat to build cash & feed reserve.
    2. Build Pastures & Buy Cows early (Days 2-10).
    3. Daily Routine: Feed Cows with Wheat, harvest Milk, sell Milk.
    4. Minimal Farmhand overhead (1-2 hands needed since animals don't need daily replanting!).
    """
    player = obs.get("player", 0)
    farms = obs.get("farms", [])
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    
    farm = farms[player]
    private = obs.get("private", {}) or {}
    market_obs = obs.get("market", {}) or {}
    prices = market_obs.get("prices", {}) or {}
    
    day = obs.get("day", 0)
    hour = obs.get("hour", 0)
    money = farm.get("money", 0.0)
    unlocked_quads = farm.get("unlocked_quadrants", ["NW"])
    tiles = farm.get("tiles", [])
    board_size = len(tiles) if tiles else 10
    half = board_size // 2
    
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})
    inventories = private.get("inventories", [{}])
    
    market_orders = []
    
    # Buy land if affordable
    land_order = ["NE", "SW", "SE"]
    land_prices = [1000, 2000, 4000]
    n_extra = len(unlocked_quads) - 1
    if n_extra < len(land_order):
        next_cost = land_prices[n_extra]
        if money >= next_cost + 300:
            market_orders.append(["BUY_LAND"])
            money -= next_cost

    # Hire 2-3 hands (low overhead!)
    target_hands = 2 if len(unlocked_quads) == 1 else (4 if len(unlocked_quads) == 2 else 6)
    hires_today = farm.get("hires_today", 0)
    if hour == 0 and hires_today < target_hands:
        def fib(n):
            a, b = 1, 1
            for _ in range(n): a, b = b, a + b
            return a
        for h in range(target_hands - hires_today):
            cost = fib(hires_today + h)
            if money >= cost + 100:
                market_orders.append(["HIRE"])
                money -= cost

    # Market Orders: Buy Cows & Wheat Seeds
    # Count how many pastures/cows we have
    cows_in_shed = shed.get("COW", 0)
    wheat_in_shed = shed.get("WHEAT", 0)
    milk_in_shed = shed.get("MILK", 0)
    
    # Sell Milk
    if milk_in_shed > 0:
        market_orders.append(["SELL", "MILK", milk_in_shed])
    # Sell extra Wheat if we have > 50
    if wheat_in_shed > 50:
        market_orders.append(["SELL", "WHEAT", wheat_in_shed - 30])
        
    # Buy Cows in early/mid game (Days 1-15)
    if day <= 15 and money >= 400 and cows_in_shed < 5 and len(market_orders) < 10:
        market_orders.append(["BUY_ANIMAL", "COW", 1])
        money -= 400
        
    # Buy Wheat Seeds to feed cows & grow wheat
    if day <= 24 and seeds.get("WHEAT", 0) < 10 and money >= 10 and len(market_orders) < 10:
        buy_w = min(10, int(money // 10))
        if buy_w > 0:
            market_orders.append(["BUY_SEED", "WHEAT", buy_w])
            money -= buy_w * 10
            
    # Workers Task Allocation
    hands = farm.get("hands", [])
    num_workers = 1 + len(hands)
    worker_positions = [farm.get("farmer", [4, 4])] + list(hands)
    shed_tiles = [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]
    
    unit_actions = []
    
    # Identify tile needs
    pasture_needed = 0
    empty_unlocked = []
    cows_placed = 0
    pastures_without_cow = []
    cows_to_feed = []
    cows_to_harvest = []
    wheat_to_water = []
    wheat_to_harvest = []
    
    for y in range(board_size):
        for x in range(board_size):
            t = tiles[y][x]
            if t == "LOCKED": continue
            if t is None:
                empty_unlocked.append((x, y))
            elif isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    if "animal" not in t or t.get("animal") is None:
                        pastures_without_cow.append((x, y))
                    elif t.get("animal") == "COW":
                        cows_placed += 1
                        if not t.get("fed_today", False):
                            cows_to_feed.append((x, y))
                        if t.get("yield_units", 0) > 0:
                            cows_to_harvest.append((x, y))
                elif kind == "PLANT":
                    if not t.get("watered_today", False):
                        wheat_to_water.append((x, y))
                    if t.get("yield_units", 0) > 0:
                        wheat_to_harvest.append((x, y))

    for w_idx in range(num_workers):
        pos = worker_positions[w_idx] if w_idx < len(worker_positions) else [4, 4]
        wx, wy = pos[0], pos[1]
        w_inv = inventories[w_idx] if w_idx < len(inventories) else {}
        inv_sum = sum(w_inv.values())
        
        w_action = ["PASS"]
        
        # If carrying items at hour >= 20 or full, drop to shed
        if (hour >= 20 and inv_sum > 0) or inv_sum >= 6:
            if (wx, wy) in shed_tiles:
                w_action = ["DROP"]
            else:
                best_s = min(shed_tiles, key=lambda s: abs(wx - s[0]) + abs(wy - s[1]))
                w_action = move_towards((wx, wy), best_s)
        else:
            t = tiles[wy][wx]
            # 1. Action on current tile
            if isinstance(t, dict):
                kind = t.get("kind")
                if kind == "PASTURE":
                    if "animal" in t and t.get("animal") == "COW":
                        if t.get("yield_units", 0) > 0:
                            w_action = ["HARVEST"]
                        elif not t.get("fed_today", False):
                            # Need wheat in inventory to feed
                            if w_inv.get("WHEAT", 0) > 0:
                                w_action = ["FEED"]
                            elif (wx, wy) in shed_tiles and shed.get("WHEAT", 0) > 0:
                                w_action = ["PICKUP", "WHEAT", 5]
                    elif "animal" not in t or t.get("animal") is None:
                        # Place cow if carrying one
                        if w_inv.get("COW", 0) > 0:
                            w_action = ["PLACE", "COW"]
                        elif (wx, wy) in shed_tiles and cows_in_shed > 0:
                            w_action = ["PICKUP", "COW", 1]
                elif kind == "PLANT":
                    if t.get("yield_units", 0) > 0:
                        w_action = ["HARVEST"]
                    elif not t.get("watered_today", False):
                        w_action = ["WATER"]
            elif t is None:
                # If we have cows in shed, build pasture here!
                if day <= 18 and (cows_in_shed > 0 or len(pastures_without_cow) < cows_in_shed):
                    w_action = ["BUILD_PASTURE"]
                elif day <= 24 and seeds.get("WHEAT", 0) > 0:
                    w_action = ["PLANT", "WHEAT"]

            # 2. Navigation if PASS
            if w_action == ["PASS"]:
                # Pick up wheat if needed and standing near shed
                if w_inv.get("WHEAT", 0) == 0 and (wx, wy) in shed_tiles and shed.get("WHEAT", 0) > 0 and cows_to_feed:
                    w_action = ["PICKUP", "WHEAT", 5]
                elif w_inv.get("COW", 0) == 0 and (wx, wy) in shed_tiles and cows_in_shed > 0 and pastures_without_cow:
                    w_action = ["PICKUP", "COW", 1]
                else:
                    targets = []
                    if cows_to_harvest: targets = cows_to_harvest
                    elif cows_to_feed and (w_inv.get("WHEAT", 0) > 0 or shed.get("WHEAT", 0) == 0): targets = cows_to_feed
                    elif wheat_to_harvest: targets = wheat_to_harvest
                    elif wheat_to_water: targets = wheat_to_water
                    elif pastures_without_cow and (w_inv.get("COW", 0) > 0 or shed.get("COW", 0) == 0): targets = pastures_without_cow
                    elif empty_unlocked and day <= 24: targets = empty_unlocked

                    if targets:
                        best = min(targets, key=lambda tgt: abs(wx - tgt[0]) + abs(wy - tgt[1]))
                        w_action = move_towards((wx, wy), best)
                    elif inv_sum > 0:
                        best_s = min(shed_tiles, key=lambda s: abs(wx - s[0]) + abs(wy - s[1]))
                        w_action = move_towards((wx, wy), best_s)
                        
        unit_actions.append(w_action)

    farmer_action = unit_actions[0] if unit_actions else ["PASS"]
    hands_actions = unit_actions[1:] if len(unit_actions) > 1 else []
    
    return {
        "farmer": farmer_action,
        "hands": hands_actions,
        "market": market_orders[:10]
    }

def move_towards(curr, target):
    cx, cy = curr
    tx, ty = target
    if cx < tx: return ["EAST"]
    elif cx > tx: return ["WEST"]
    elif cy < ty: return ["SOUTH"]
    elif cy > ty: return ["NORTH"]
    return ["PASS"]
