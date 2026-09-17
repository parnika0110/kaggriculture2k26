"""Ablation benchmark: isolate frontload() and advance_sales() effects.

Variants:
  A = V43+C9 (original)
  B = V43+C9 + frontload only
  C = V43+C9 + advance_sales only
  D = V43+C9 + frontload + advance_sales
"""
import json, sys, time, math, copy
sys.path.insert(0, '.')
from kaggle_environments import make

# ============================================================
# Load base V43+C9 agent (from backup, no V7 features)
# ============================================================
base_globals = {}
exec(open('submission_v43c9_backup.py', encoding='utf-8').read(), base_globals)
base_agent = base_globals['agent']

# ============================================================
# Extract frontload() and advance_sales() from enhanced agent
# ============================================================
# We need to import the V7 helper functions from the enhanced file
enhanced_globals = {}
exec(open('submission.py', encoding='utf-8').read(), enhanced_globals)

frontload_fn = enhanced_globals['_v7_frontload']
advance_sales_fn = enhanced_globals['_v7_advance_sales']
future_market_fn = enhanced_globals['_v7_future_market']
standard_fn = enhanced_globals['_v7_standard']
v7_telemetry = enhanced_globals['_V7_TELEMETRY']

# ============================================================
# Variant wrappers
# ============================================================
def agent_a(obs, config=None):
    """A: Pure V43+C9"""
    return base_agent(obs, config)

def agent_b(obs, config=None):
    """B: V43+C9 + frontload only"""
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = frontload_fn(obs, m, None, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

def agent_c(obs, config=None):
    """C: V43+C9 + advance_sales only"""
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = advance_sales_fn(obs, m, future_market_fn, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

def agent_d(obs, config=None):
    """D: V43+C9 + frontload + advance_sales"""
    action = base_agent(obs, config)
    try:
        if isinstance(action, dict) and standard_fn(config):
            m = action.get("market")
            m = list(m) if isinstance(m, list) else []
            new = advance_sales_fn(obs, m, future_market_fn, None)
            if len(new) > 1:
                new = frontload_fn(obs, new, None, None)
            if new is not m:
                action = dict(action); action["market"] = new
    except Exception:
        pass
    return action

# ============================================================
# Run benchmark
# ============================================================
SEEDS = list(range(5))
CONFIG = {
    "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
    "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
    "farmHandCostMult": 1,
    "seed": 0,  # placeholder, overridden per-run
}

def run_one(agent_fn, seed):
    cfg = dict(CONFIG); cfg["seed"] = seed
    env = make("kaggriculture", debug=True, configuration=cfg)
    trainer = env.train([None, "random"])
    obs = trainer.reset()
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_fn(obs_json)
        obs, reward, done, info = trainer.step(action)
    return reward

results = {name: [] for name in ["A", "B", "C", "D"]}
agents = {"A": agent_a, "B": agent_b, "C": agent_c, "D": agent_d}

print(f"Running {len(SEEDS)} seeds x 4 variants = {len(SEEDS)*4} games...")
t0 = time.time()

for seed in SEEDS:
    for name, fn in agents.items():
        score = run_one(fn, seed)
        results[name].append(score)
    # Print progress
    a, b, c, d = results["A"][-1], results["B"][-1], results["C"][-1], results["D"][-1]
    best = max(a, b, c, d)
    winner = "A" if a == best else "B" if b == best else "C" if c == best else "D"
    print(f"Seed {seed:2d}: A=${a:>9,.0f}  B=${b:>9,.0f}  C=${c:>9,.0f}  D=${d:>9,.0f}  [{winner}]")

elapsed = time.time() - t0
print(f"\nCompleted in {elapsed:.0f}s ({elapsed/len(SEEDS)/4:.1f}s per game)")

# ============================================================
# Statistical summary
# ============================================================
def stats(scores):
    n = len(scores)
    mean = sum(scores) / n
    median = sorted(scores)[n // 2]
    mn = min(scores)
    mx = max(scores)
    var = sum((x - mean) ** 2 for x in scores) / n
    stdev = math.sqrt(var)
    total = sum(scores)
    return {"mean": mean, "median": median, "min": mn, "max": mx, "stdev": stdev, "total": total}

print("\n" + "=" * 80)
print("PER-SEED TABLE")
print("=" * 80)
print(f"{'seed':>4s} | {'A (base)':>12s} | {'B (+front)':>12s} | {'C (+adv)':>12s} | {'D (+both)':>12s} | winner")
print("-" * 80)
for i, seed in enumerate(SEEDS):
    a, b, c, d = results["A"][i], results["B"][i], results["C"][i], results["D"][i]
    best = max(a, b, c, d)
    w = "A" if a == best else "B" if b == best else "C" if c == best else "D"
    print(f"{seed:4d} | ${a:>10,.0f} | ${b:>10,.0f} | ${c:>10,.0f} | ${d:>10,.0f} | {w}")

print("\n" + "=" * 80)
print("STATISTICAL SUMMARY")
print("=" * 80)
print(f"{'Metric':<15s} | {'A (base)':>12s} | {'B (+front)':>12s} | {'C (+adv)':>12s} | {'D (+both)':>12s}")
print("-" * 80)
for metric in ["mean", "median", "min", "max", "stdev", "total"]:
    vals = []
    for name in ["A", "B", "C", "D"]:
        s = stats(results[name])
        vals.append(s[metric])
    label = metric if metric != "total" else "total_score"
    print(f"{label:<15s} | ${vals[0]:>10,.0f} | ${vals[1]:>10,.0f} | ${vals[2]:>10,.0f} | ${vals[3]:>10,.0f}")

# Pairwise win/loss/tie
print("\n" + "=" * 80)
print("PAIRWISE WIN/LOSS/TIE COUNTS")
print("=" * 80)
for x_name in ["A", "B", "C", "D"]:
    for y_name in ["A", "B", "C", "D"]:
        if x_name >= y_name:
            continue
        wins = sum(1 for x, y in zip(results[x_name], results[y_name]) if x > y)
        losses = sum(1 for x, y in zip(results[x_name], results[y_name]) if x < y)
        ties = len(SEEDS) - wins - losses
        diff = stats(results[x_name])["mean"] - stats(results[y_name])["mean"]
        print(f"  {x_name} vs {y_name}: {wins}W-{losses}L-{ties}T  (mean diff: ${diff:+,.0f})")

# ============================================================
# Investigate seeds 9, 10, 11
# ============================================================
print("\n" + "=" * 80)
print("BAD SEED INVESTIGATION (9, 10, 11)")
print("=" * 80)

for seed in [3, 4]:
    a_score = results["A"][seed]
    b_score = results["B"][seed]
    c_score = results["C"][seed]
    d_score = results["D"][seed]
    print(f"\nSeed {seed}: A=${a_score:,.0f}  B=${b_score:,.0f}  C=${c_score:,.0f}  D=${d_score:,.0f}")
    print(f"  B vs A: ${b_score - a_score:+,.0f}")
    print(f"  C vs A: ${c_score - a_score:+,.0f}")
    print(f"  D vs A: ${d_score - a_score:+,.0f}")
    
    # Determine which feature causes the problem
    # If B ≈ A but C deviates: advance_sales is the problem
    # If C ≈ A but B deviates: frontload is the problem
    # If both deviate: both contribute
    
    b_diff = abs(b_score - a_score)
    c_diff = abs(c_score - a_score)
    
    if b_diff < 5000 and c_diff >= 5000:
        print(f"  DIAGNOSIS: advance_sales is the culprit (B stable, C varies)")
    elif c_diff < 5000 and b_diff >= 5000:
        print(f"  DIAGNOSIS: frontload is the culprit (C stable, B varies)")
    elif b_diff >= 5000 and c_diff >= 5000:
        print(f"  DIAGNOSIS: both features contribute")
    else:
        print(f"  DIAGNOSIS: both features stable, interaction effect")

# ============================================================
# Deep dive: trace the first divergence on bad seeds
# ============================================================
print("\n" + "=" * 80)
print("FIRST DIVERGENCE TRACE (bad seeds)")
print("=" * 80)

for seed in [3, 4]:
    print(f"\n--- Seed {seed} ---")
    
    # Run A and D side by side, tracking actions step by step
    cfg = dict(CONFIG); cfg["seed"] = seed
    env_a = make("kaggriculture", debug=True, configuration=cfg)
    trainer_a = env_a.train([None, "random"])
    obs_a = trainer_a.reset()
    
    env_d = make("kaggriculture", debug=True, configuration=cfg)
    trainer_d = env_d.train([None, "random"])
    obs_d = trainer_d.reset()
    
    step = 0
    first_diverge = None
    while not trainer_a.done and not trainer_d.done:
        obs_json_a = json.loads(json.dumps(obs_a))
        obs_json_d = json.loads(json.dumps(obs_d))
        
        action_a = agent_a(obs_json_a)
        action_d = agent_d(obs_json_d)
        
        # Compare market orders
        mkt_a = action_a.get("market", [])
        mkt_d = action_d.get("market", [])
        
        if mkt_a != mkt_d and first_diverge is None:
            first_diverge = step
            day = step // 24
            hour = step % 24
            print(f"  First market divergence at step {step} (day {day}, hour {hour}):")
            print(f"    A market: {mkt_a}")
            print(f"    D market: {mkt_d}")
            
            # Find what was added/changed
            a_sells = [o for o in mkt_a if isinstance(o, list) and o[0] == "SELL"]
            d_sells = [o for o in mkt_d if isinstance(o, list) and o[0] == "SELL"]
            a_buys = [o for o in mkt_a if isinstance(o, list) and o[0] == "BUY_PRODUCT"]
            d_buys = [o for o in mkt_d if isinstance(o, list) and o[0] == "BUY_PRODUCT"]
            
            print(f"    A: {len(a_sells)} sells, {len(a_buys)} buys")
            print(f"    D: {len(d_sells)} sells, {len(d_buys)} buys")
            
            # Identify extra sells in D
            d_sell_items = {}
            for o in d_sells:
                item = o[1]
                d_sell_items[item] = d_sell_items.get(item, 0) + int(o[2])
            a_sell_items = {}
            for o in a_sells:
                item = o[1]
                a_sell_items[item] = a_sell_items.get(item, 0) + int(o[2])
            
            for item in set(list(a_sell_items.keys()) + list(d_sell_items.keys())):
                a_q = a_sell_items.get(item, 0)
                d_q = d_sell_items.get(item, 0)
                if a_q != d_q:
                    print(f"    SELL {item}: A={a_q} units, D={d_q} units (diff: {d_q-a_q:+d})")
        
        # Compare scores
        money_a = obs_a["farms"][0]["money"]
        money_d = obs_d["farms"][0]["money"]
        if step <= first_diverge + 5 if first_diverge else step < 5:
            if abs(money_a - money_d) > 1:
                day = step // 24
                hour = step % 24
                print(f"    Step {step} (D{day}H{hour}): A=${money_a:,.0f} D=${money_d:,.0f} diff=${money_d-money_a:+,.0f}")
        
        obs_a, _, done_a, _ = trainer_a.step(action_a)
        obs_d, _, done_d, _ = trainer_d.step(action_d)
        step += 1
    
    final_a = obs_a["farms"][0]["money"]
    final_d = obs_d["farms"][0]["money"]
    print(f"  Final: A=${final_a:,.0f}  D=${final_d:,.0f}  diff=${final_d-final_a:+,.0f}")
