"""
Kaggriculture V7 — Correct Ongoing-Water + Lean Capital
=========================================================

Critical engine rules (from source read):
  - Ongoing crops (TOMATO, STRAWBERRY) die after 2 *consecutive* unwatered days
  - `yield_units > 0` does NOT exempt an ongoing plant from needing water
  - WATER for ongoing crops sets watered_today=True; yield added at end-of-day daily refresh
  - WATER for non-ongoing crops adds yield ONLY in window [ceil(max_yield_day/2) .. max_yield_day]
  - Atomic PLANT validation: if #PLANT(crop) > seeds[crop] this step, ALL blocked for that crop
  - Workers expire every night; re-hire at hour 0 daily (fib costs: 1,1,2,3,5,8...)
  - Market runs EVERY step (hour); buy animals/land only at hour 0 to avoid over-purchasing

Strategy:
  - NO land purchase (NW quadrant = 21 tiles, 6 workers can cover all of them)
  - WHEAT days 0-3 (fast 2-day yield, cheap $10, gives $25-$100 per plant, no daily water needed)
  - TOMATO days 2-16 (ongoing, water EVERY day or dies; $60 base × 4 yield = $240/plant)
  - HIRE 5 workers daily (fib cost 1+1+2+3+5=$12/day = $360 total)
  - Total capital plan: $3000 - $560 (seeds) - $360 (hire) = $2080 available for revenue
  - 15 TOMATO plants × $240 = $3600 revenue → final score ~$5000+ goal

Bug fixed: ongoing crops get WATER task even when yield_units > 0.
Separate claimed sets for WATER vs HARVEST so same tile can receive both.
"""

CROP_INFO = {
    "WHEAT":      {"seed": 10,  "first": 2, "max_day": 4,  "max_yield": 6, "ongoing": False},
    "CARROT":     {"seed": 20,  "first": 2, "max_day": 3,  "max_yield": 4, "ongoing": False},
    "TOMATO":     {"seed": 50,  "first": 8, "max_day": 8,  "max_yield": 4, "ongoing": True,  "interval": 1},
    "STRAWBERRY": {"seed": 100, "first": 10,"max_day": 10, "max_yield": 4, "ongoing": True,  "interval": 2},
}


def _move(curr, tgt):
    cx, cy = curr; tx, ty = tgt
    if cx < tx: return ["EAST"]
    if cx > tx: return ["WEST"]
    if cy < ty: return ["SOUTH"]
    if cy > ty: return ["NORTH"]
    return ["PASS"]


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _nearest(pos, lst):
    return min(lst, key=lambda p: _dist(pos, p))


def agent(obs, config=None):
    player = obs.get("player", 0)
    farms  = obs.get("farms", [])
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm    = farms[player]
    private = obs.get("private", {}) or {}
    prices  = (obs.get("market", {}) or {}).get("prices", {}) or {}

    day   = obs.get("day", 0)
    hour  = obs.get("hour", 0)
    money = farm.get("money", 0.0)

    seeds = private.get("seeds", {}) or {}
    shed  = private.get("shed",  {}) or {}
    invs  = private.get("inventories", [{}])

    tiles_raw = farm.get("tiles", [])
    board_h   = len(tiles_raw)
    board_w   = len(tiles_raw[0]) if board_h > 0 else 10
    half      = board_h // 2

    # Shed = 4 center tiles
    shed_set  = {(half-1, half-1), (half, half-1), (half-1, half), (half, half)}
    shed_list = list(shed_set)

    hands_list  = farm.get("hands", [])
    num_workers = 1 + len(hands_list)
    w_pos = ([tuple(farm.get("farmer", [half-1, half-1]))]
             + [tuple(h) for h in hands_list])

    # ── TILE SCAN ─────────────────────────────────────────────────────────────
    # ALL crops die after 2 consecutive unwatered days (planting day = 1 already).
    # So every unwatered plant must be tracked; urgency depends on consecutive count.
    water_critical = []  # consecutive_unwatered >= 1 → will die tonight if not watered NOW
    water_normal   = []  # consecutive_unwatered == 0 → safe today, water for yield/survival
    harvest_ready  = []  # plants with yield_units > 0
    empty_tiles    = []

    for y in range(board_h):
        for x in range(board_w):
            t   = tiles_raw[y][x]
            pos = (x, y)
            if pos in shed_set or t == "LOCKED":
                continue
            if t is None:
                empty_tiles.append(pos)
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                crop      = t.get("crop", "")
                cd        = CROP_INFO.get(crop, {})
                watered   = t.get("watered_today", False)
                yield_u   = t.get("yield_units", 0)
                age       = day - t.get("planted_day", 0)
                ongoing   = cd.get("ongoing", False)
                cons_uw   = t.get("consecutive_unwatered", 0)

                if not watered:
                    if cons_uw >= 1:
                        # Last chance — will become weed tonight if not watered
                        water_critical.append((pos, ongoing))
                    else:
                        # Safe for now but water for yield bonus / future safety
                        water_normal.append((pos, ongoing))

                # Harvest: ongoing only after watering (else it might die tonight)
                if yield_u > 0:
                    if ongoing:
                        if watered:  # safe to harvest — already watered today
                            harvest_ready.append((pos, crop))
                        # else: will be watered first (critical), then harvested next hour
                    else:
                        if age >= cd.get("first", 2):
                            harvest_ready.append((pos, crop))

    # ── MARKET ORDERS ─────────────────────────────────────────────────────────
    market = []

    # Sell all crops from shed
    for crop in ["TOMATO", "STRAWBERRY", "WHEAT", "CARROT", "MELON"]:
        amt = shed.get(crop, 0)
        if amt > 0 and len(market) < 10:
            market.append(["SELL", crop, amt])

    # Hire at start of each day (fib costs stay cheap for 5 workers)
    if hour == 0:
        hires = farm.get("hires_today", 0)
        target = 5
        for i in range(target - hires):
            n = hires + i
            a, b = 1, 1
            for _ in range(n):
                a, b = b, a + b
            cost = a  # fib(n)
            if money >= cost + 30 and len(market) < 10:
                market.append(["HIRE"])
                money -= cost
            else:
                break

    # Buy WHEAT seeds early (days 0-4, cheap $10, quick yield in 2 days)
    if day <= 4 and money >= 100:
        n_wheat = seeds.get("WHEAT", 0)
        n_empty = len(empty_tiles)
        want    = min(n_empty, 15)
        if n_wheat < want and len(market) < 10:
            buy_n = min(want - n_wheat, int((money - 50) // 10))
            if buy_n > 0:
                market.append(["BUY_SEED", "WHEAT", buy_n])
                money -= buy_n * 10

    # Buy TOMATO seeds (days 2-16, $50 each, 15 target)
    if 2 <= day <= 16 and money >= 200:
        n_tom = seeds.get("TOMATO", 0)
        want  = min(len(empty_tiles), 15)
        if n_tom < want and len(market) < 10:
            buy_n = min(want - n_tom, int((money - 100) // 50))
            if buy_n > 0:
                market.append(["BUY_SEED", "TOMATO", buy_n])
                money -= buy_n * 50

    # ── TASK POOL ─────────────────────────────────────────────────────────────
    # Two separate claimed sets: one for WATER tasks, one for HARVEST/PLANT tasks.
    # This lets the same tile appear in both (ongoing plant needs both water and harvest).

    # Best seed to plant
    plant_seed = None
    plant_count = 0
    for s in ["TOMATO", "WHEAT", "CARROT"]:
        cnt = seeds.get(s, 0)
        if cnt > 0:
            plant_seed  = s
            plant_count = cnt
            break

    # Tasks: (priority, type, pos)
    tasks_water  = [(5,  "WATER", p) for p, _ in water_critical]   # die tonight without water
    tasks_water += [(20, "WATER", p) for p, _ in water_normal]     # yield window / next-day safety
    tasks_action = [(10, "HARVEST", p) for p, _ in harvest_ready]
    if plant_seed and plant_count > 0:
        for i, p in enumerate(empty_tiles):
            if i >= plant_count:
                break
            tasks_action.append((30, "PLANT", p))

    tasks_water.sort(key=lambda x: x[0])
    tasks_action.sort(key=lambda x: x[0])

    # ── ASSIGN WORKERS ────────────────────────────────────────────────────────
    claimed_water  = set()
    claimed_action = set()
    local_seeds    = dict(seeds)  # mutable copy to track plant budget
    w_actions      = []

    for wi in range(num_workers):
        wx, wy  = w_pos[wi]
        w_inv   = invs[wi] if wi < len(invs) else {}
        inv_tot = sum(w_inv.values())

        # Force drop if inventory full or near end of day
        if inv_tot >= 6 or (hour >= 22 and inv_tot > 0):
            if (wx, wy) in shed_set:
                w_actions.append(["DROP"])
            else:
                w_actions.append(_move((wx, wy), _nearest((wx, wy), shed_list)))
            continue

        # Find best water task (priority then distance)
        best_water = None
        best_water_score = 999999
        for pri, ttype, tpos in tasks_water:
            if tpos in claimed_water:
                continue
            score = pri * 1000 + _dist((wx, wy), tpos)
            if score < best_water_score:
                best_water_score = score
                best_water = (pri, ttype, tpos)

        # Find best action task (priority then distance)
        best_action = None
        best_action_score = 999999
        for pri, ttype, tpos in tasks_action:
            if tpos in claimed_action:
                continue
            if ttype == "PLANT" and local_seeds.get(plant_seed, 0) <= 0:
                continue
            score = pri * 1000 + _dist((wx, wy), tpos)
            if score < best_action_score:
                best_action_score = score
                best_action = (pri, ttype, tpos)

        # Pick whichever task is closer (accounting for priority weighting)
        chosen = None
        if best_water and best_action:
            chosen = best_water if best_water_score <= best_action_score else best_action
        elif best_water:
            chosen = best_water
        elif best_action:
            chosen = best_action

        if chosen is None:
            # Nothing to do; wait at or move toward shed
            if (wx, wy) not in shed_set:
                w_actions.append(_move((wx, wy), _nearest((wx, wy), shed_list)))
            else:
                w_actions.append(["PASS"])
            continue

        _, ttype, tpos = chosen
        if ttype == "WATER":
            claimed_water.add(tpos)
        else:
            claimed_action.add(tpos)

        tx, ty   = tpos
        tile_at  = tiles_raw[ty][tx]

        if (wx, wy) == tpos:
            if ttype == "WATER":
                w_actions.append(["WATER"])
            elif ttype == "HARVEST":
                w_actions.append(["HARVEST"])
            elif ttype == "PLANT":
                if tile_at is None and local_seeds.get(plant_seed, 0) > 0:
                    w_actions.append(["PLANT", plant_seed])
                    local_seeds[plant_seed] -= 1
                else:
                    w_actions.append(["PASS"])
            else:
                w_actions.append(["PASS"])
        else:
            w_actions.append(_move((wx, wy), tpos))

    farmer_act = w_actions[0] if w_actions else ["PASS"]
    hands_acts = w_actions[1:] if len(w_actions) > 1 else []

    return {
        "farmer": farmer_act,
        "hands":  hands_acts,
        "market": market[:10],
    }
