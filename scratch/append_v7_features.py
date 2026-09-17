"""Append V7 market simulation features to submission.py."""

V7_CODE = '''

# ============================================================
# V7 MARKET SIMULATION FEATURES (ported from reactive-v7)
# frontload: reorder SELLs before BUY_PRODUCTs for better prices
# advance_sales: pre-sell items from future tape steps
# ============================================================
import math as _math

_V7_MARKET_I0 = 10000
_V7_PRICE_FLOOR = 1
_V7_HINGE_GAIN = 8.0
_V7_MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "I0": _V7_MARKET_I0, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "I0": _V7_MARKET_I0, "T": 450, "below_func": "hinge",  "below_target": 1.00, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "I0": _V7_MARKET_I0, "T": 200, "below_func": "hinge",  "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "I0": _V7_MARKET_I0, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "I0": _V7_MARKET_I0, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "I0": _V7_MARKET_I0, "T": 332, "below_func": "hinge",  "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "I0": _V7_MARKET_I0, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "I0": _V7_MARKET_I0, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "I0": _V7_MARKET_I0, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}
_V7_SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
_V7_ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
_V7_LAND_PRICES = [1000, 2000, 4000]


def _v7_shape(func, x, T=None):
    x = max(0.0, x)
    if func == "linear": return x
    if func == "sq": return x * x
    if func == "sqrt": return _math.sqrt(x)
    if func == "log": return _math.log(1.0 + x)
    if func == "hinge":
        if not T or T <= 0: return x
        u = x / T
        return u + _V7_HINGE_GAIN * max(0.0, u - 1.0) ** 2
    return x


def _v7_price(item, inventory, params=None):
    p = (params or _V7_MARKET_PARAMS)[item]
    base, I0, T = p["base"], p["I0"], p["T"]
    if inventory < I0:
        amp = p["below_target"] * base / _v7_shape(p["below_func"], T, T)
        v = base + amp * _v7_shape(p["below_func"], I0 - inventory, T)
    else:
        amp = p["above_target"] * base / _v7_shape(p["above_func"], T, T)
        v = base - amp * _v7_shape(p["above_func"], inventory - I0, T)
    return max(_V7_PRICE_FLOOR, int(round(v)))


def _v7_fib(n):
    a, b = 1, 1
    for _ in range(n): a, b = b, a + b
    return a


def _v7_simulate(orders, money, shed_total, inv, hires_today, n_land_extra, params=None, opp_pressure=0):
    params = params or _V7_MARKET_PARAMS
    inv = dict(inv); money = float(money); shed = int(shed_total)
    for o in orders:
        if not isinstance(o, (list, tuple)) or not o: return False, money
        op = o[0]
        if op == "HIRE":
            c = _v7_fib(hires_today)
            if money < c: return False, money
            money -= c; hires_today += 1; continue
        if op == "BUY_LAND":
            if n_land_extra >= len(_V7_LAND_PRICES): return False, money
            c = _V7_LAND_PRICES[n_land_extra]
            if money < c: return False, money
            money -= c; n_land_extra += 1; continue
        if len(o) < 3: return False, money
        try: n = int(o[2])
        except Exception: return False, money
        if n <= 0: return False, money
        item = o[1]
        if op == "SELL":
            if item not in params: return False, money
            for _ in range(n):
                p = _v7_price(item, inv[item], params)
                money += p
                if p > 1: inv[item] += 1 + opp_pressure
                shed -= 1
        elif op == "BUY_PRODUCT":
            if item not in ("WHEAT", "FERTILIZER"): return False, money
            for _ in range(n):
                p = _v7_price(item, inv[item] - 1, params)
                if money < p or shed >= 100: return False, money
                money -= p; inv[item] -= 1 + opp_pressure; shed += 1
        elif op == "BUY_SEED":
            if item not in _V7_SEED_COST: return False, money
            c = _V7_SEED_COST[item] * n
            if money < c: return False, money
            money -= c
        elif op == "BUY_ANIMAL":
            if item not in _V7_ANIMAL_COST: return False, money
            for _ in range(n):
                c = _V7_ANIMAL_COST[item]
                if money < c or shed >= 100: return False, money
                money -= c; shed += 1
        else:
            return False, money
    return True, money


_V7_PREMIUM = ("STRAWBERRY", "WOOL", "EGG", "MILK", "MELON", "CARROT", "TOMATO")


def _v7_frontload(obs, market, params=None, telemetry=None):
    if not isinstance(market, list) or len(market) < 2: return market
    orders = [list(o) for o in market if isinstance(o, (list, tuple)) and o]
    if len(orders) != len(market): return market
    A, B, C = [], [], []
    for j, o in enumerate(orders):
        op = o[0]
        if op == "SELL":
            wash = any(p[0] == "BUY_PRODUCT" and len(p) > 1 and len(o) > 1 and p[1] == o[1] for p in orders[:j])
            (B if wash else A).append(o)
        elif op == "BUY_PRODUCT":
            B.append(o)
        else:
            C.append(o)
    new = A + B + C
    if new == orders: return market
    try:
        me = int(obs["player"]); farm = obs["farms"][me]; private = obs["private"]
        money = float(farm["money"]); shed_total = sum(int(v) for v in private["shed"].values())
        inv = {k: int(v) for k, v in obs["market"]["inventory"].items()}
        hires_today = int(farm.get("hires_today", 0)); n_land_extra = max(0, len(farm.get("unlocked_quadrants", ["NW"])) - 1)
        for pressure in (0, 1):
            ok_old, _ = _v7_simulate(orders, money, shed_total, inv, hires_today, n_land_extra, params, pressure)
            ok_new, _ = _v7_simulate(new, money, shed_total, inv, hires_today, n_land_extra, params, pressure)
            if not ok_old or not ok_new:
                if telemetry is not None: telemetry["frontload_declined"] = telemetry.get("frontload_declined", 0) + 1
                return market
    except Exception:
        return market
    if telemetry is not None:
        telemetry["frontload_turns"] = telemetry.get("frontload_turns", 0) + 1
    return new


_V7_LOOKAHEAD = 2
_V7_MIN_UNITS = 1


def _v7_advance_sales(obs, market, future_market_fn, telemetry=None, max_orders=10, items=_V7_PREMIUM):
    try:
        step = int(obs["step"])
        if step % 24 == 23 or step >= 718:
            return market
        nxt = []
        for off in range(1, _V7_LOOKAHEAD + 1):
            m_off = future_market_fn(obs, off) if _V7_LOOKAHEAD > 1 else future_market_fn(obs)
            if m_off:
                nxt += [o for o in m_off if isinstance(o, (list, tuple)) and o]
        if not nxt:
            return market
        want = {}
        first = next((o for o in nxt if isinstance(o, (list, tuple)) and o), None)
        protected = first[1] if first and len(first) > 2 and first[0] == "SELL" else None
        for o in nxt:
            if isinstance(o, (list, tuple)) and len(o) > 2 and o[0] == "SELL" and o[1] in items and o[1] != protected:
                try: want[o[1]] = want.get(o[1], 0) + max(0, int(o[2]))
                except Exception: pass
        if not want:
            return market
        shed = obs["private"]["shed"]
        cur = [list(o) for o in (market or []) if isinstance(o, (list, tuple)) and o]
        selling_now = {}
        for o in cur:
            if len(o) > 2 and o[0] == "SELL":
                try: selling_now[o[1]] = selling_now.get(o[1], 0) + max(0, int(o[2]))
                except Exception: pass
        extra = []; merged = 0
        for item, q in want.items():
            avail = int(shed.get(item, 0)) - selling_now.get(item, 0)
            n = min(q, avail)
            if n < _V7_MIN_UNITS:
                continue
            hit = next((o for o in cur if len(o) > 2 and o[0] == "SELL" and o[1] == item), None)
            if hit is not None:
                hit[2] = int(hit[2]) + n; merged += n
            else:
                extra.append(["SELL", item, n])
        if len(cur) + len(extra) > max_orders:
            extra = extra[:max(0, max_orders - len(cur))]
        if not extra and not merged:
            return market
        if telemetry is not None:
            telemetry["advance_turns"] = telemetry.get("advance_turns", 0) + 1
            telemetry["advance_units"] = telemetry.get("advance_units", 0) + sum(e[2] for e in extra) + merged
        return extra + cur
    except Exception:
        return market


_V7_TELEMETRY = {}


def _v7_future_market(obs, offset=1):
    try:
        step = int(obs["step"]) + offset
        if step >= 719:
            return None
        impl = _IMPL
        players = impl.chassis.players
        native = players.get(int(obs["player"])) if isinstance(players, dict) else None
        route = 2 if step >= 648 else (native or {}).get("route")
        if route is None:
            return None
        return impl.chassis.routes[route][step].get("market")
    except Exception:
        return None


def _v7_standard(configuration):
    if configuration is None: return True
    try:
        for k, v in (("boardSize", 10), ("turnsPerDay", 24), ("shedCapacity", 100), ("maxMarketOrdersPerTurn", 10), ("farmHandCostMult", 1)):
            if configuration.get(k, v) != v: return False
        if configuration.get("marketParams", None): return False
    except Exception:
        return False
    return True


# Wrap the existing agent with V7 market simulation
_PARENT_V7 = agent
del agent


def agent(observation, configuration=None):
    action = _PARENT_V7(observation, configuration)
    try:
        if isinstance(action, dict) and _v7_standard(configuration):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = _v7_advance_sales(observation, m, _v7_future_market, _V7_TELEMETRY)
            if len(new) > 1:
                new = _v7_frontload(observation, new, None, _V7_TELEMETRY)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        _V7_TELEMETRY["wrap_errors"] = _V7_TELEMETRY.get("wrap_errors", 0) + 1
    return action
'''

with open('submission.py', 'a', encoding='utf-8') as f:
    f.write(V7_CODE)

print("Done. Appended V7 market simulation features.")
