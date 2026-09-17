"""Deep ablation investigation.

Key finding from 5-seed ablation:
  A (base):    mean $152,063
  B (+front):  mean $140,707  <- HURTS by $11K
  C (+adv):    mean $166,534  <- HELPS by $14K
  D (+both):   mean $157,565  <- frontload drags down advance_sales

Hypothesis: frontload() reorders SELL before BUY_PRODUCT, which can
change which order gets the better price in the lockstep market.
When the parent agent's tape has [BUY_SEED, SELL], frontload moves
the SELL first. But the SELL quantity might be capped by what's in
the shed, and executing SELL first reduces shed capacity before the
BUY_PRODUCT, potentially blocking the buy.

Test: run 10 seeds, trace every frontload and advance_sales action.
"""
import json, sys, time, math
sys.path.insert(0, '.')
from kaggle_environments import make

base_globals = {}
exec(open('submission_v43c9_backup.py', encoding='utf-8').read(), base_globals)
base_agent = base_globals['agent']

enhanced_globals = {}
exec(open('submission.py', encoding='utf-8').read(), enhanced_globals)
frontload_fn = enhanced_globals['_v7_frontload']
advance_sales_fn = enhanced_globals['_v7_advance_sales']
future_market_fn = enhanced_globals['_v7_future_market']
standard_fn = enhanced_globals['_v7_standard']

SEEDS = list(range(10))
CONFIG = {"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}

# ============================================================
# Track frontload and advance_sales effects per step
# ============================================================
def run_tracked(agent_fn, seed, label):
    cfg = dict(CONFIG); cfg["seed"] = seed
    env = make("kaggriculture", debug=True, configuration=cfg)
    trainer = env.train([None, "random"])
    obs = trainer.reset()
    done = False
    frontload_count = 0
    advance_count = 0
    advance_units = 0
    frontload_declined = 0
    money_history = []
    step = 0
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_fn(obs_json)
        obs, reward, done, info = trainer.step(action)
        money_history.append(obs["farms"][0]["money"])
        step += 1
    return {
        "score": reward,
        "frontload_count": frontload_count,
        "advance_count": advance_count,
        "advance_units": advance_units,
        "money_history": money_history,
    }

# ============================================================
# Compare A vs B (frontload effect) and A vs C (advance effect)
# ============================================================
print("Running A vs B (frontload) and A vs C (advance_sales)...")
t0 = time.time()

# Simple A agent
def agent_a(obs, config=None):
    return base_agent(obs, config)

# B: frontload only
def agent_b(obs, config=None):
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

# C: advance_sales only
def agent_c(obs, config=None):
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

a_scores, b_scores, c_scores = [], [], []
for seed in SEEDS:
    cfg = dict(CONFIG); cfg["seed"] = seed
    
    # Run A
    env = make("kaggriculture", debug=True, configuration=cfg)
    t = env.train([None, "random"])
    obs = t.reset()
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_a(obs_json)
        obs, reward_a, done, info = t.step(action)
    
    # Run B
    env = make("kaggriculture", debug=True, configuration=cfg)
    t = env.train([None, "random"])
    obs = t.reset()
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_b(obs_json)
        obs, reward_b, done, info = t.step(action)
    
    # Run C
    env = make("kaggriculture", debug=True, configuration=cfg)
    t = env.train([None, "random"])
    obs = t.reset()
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent_c(obs_json)
        obs, reward_c, done, info = t.step(action)
    
    a_scores.append(reward_a)
    b_scores.append(reward_b)
    c_scores.append(reward_c)
    
    front_diff = reward_b - reward_a
    adv_diff = reward_c - reward_a
    print(f"Seed {seed:2d}: A=${reward_a:>9,.0f}  B-A=${front_diff:>+9,.0f}  C-A=${adv_diff:>+9,.0f}")

elapsed = time.time() - t0
print(f"\nCompleted in {elapsed:.0f}s")

# ============================================================
# Statistics
# ============================================================
def mean(lst): return sum(lst) / len(lst)
def stdev(lst):
    m = mean(lst)
    return math.sqrt(sum((x - m) ** 2 for x in lst) / len(lst))

print(f"\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
print(f"A (base)     mean: ${mean(a_scores):>10,.0f}  stdev: ${stdev(a_scores):>8,.0f}")
print(f"B (+front)   mean: ${mean(b_scores):>10,.0f}  stdev: ${stdev(b_scores):>8,.0f}")
print(f"C (+adv)     mean: ${mean(c_scores):>10,.0f}  stdev: ${stdev(c_scores):>8,.0f}")
print(f"\nB vs A: ${mean(b_scores)-mean(a_scores):>+,.0f} ({(mean(b_scores)-mean(a_scores))/mean(a_scores)*100:+.1f}%)")
print(f"C vs A: ${mean(c_scores)-mean(a_scores):>+,.0f} ({(mean(c_scores)-mean(a_scores))/mean(a_scores)*100:+.1f}%)")

b_wins = sum(1 for x, y in zip(b_scores, a_scores) if x > y)
c_wins = sum(1 for x, y in zip(c_scores, a_scores) if x > y)
print(f"\nB beats A: {b_wins}/{len(SEEDS)}")
print(f"C beats A: {c_wins}/{len(SEEDS)}")

# ============================================================
# Investigate seed 0: frontload costs $36K
# ============================================================
print(f"\n{'='*60}")
print("SEED 0: frontload costs $36K — trace")
print(f"{'='*60}")

cfg = dict(CONFIG); cfg["seed"] = 0

# Run A and B side by side, comparing market orders
env_a = make("kaggriculture", debug=True, configuration=cfg)
t_a = env_a.train([None, "random"])
obs_a = t_a.reset()

env_b = make("kaggriculture", debug=True, configuration=cfg)
t_b = env_b.train([None, "random"])
obs_b = t_b.reset()

step = 0
divergences = []
done_a = False
while not done_a:
    obs_json_a = json.loads(json.dumps(obs_a))
    obs_json_b = json.loads(json.dumps(obs_b))
    
    action_a = agent_a(obs_json_a)
    action_b = agent_b(obs_json_b)
    
    mkt_a = json.dumps(action_a.get("market", []))
    mkt_b = json.dumps(action_b.get("market", []))
    
    if mkt_a != mkt_b:
        day = step // 24
        hour = step % 24
        divergences.append({
            "step": step, "day": day, "hour": hour,
            "a_market": action_a.get("market", []),
            "b_market": action_b.get("market", []),
            "a_money": obs_a["farms"][0]["money"],
            "b_money": obs_b["farms"][0]["money"],
        })
    
    obs_a, _, done_a, _ = t_a.step(action_a)
    obs_b, _, _, _ = t_b.step(action_b)
    step += 1

print(f"Total divergences: {len(divergences)}")
for d in divergences[:10]:  # Show first 10
    print(f"\nStep {d['step']} (D{d['day']}H{d['hour']}):")
    print(f"  A money: ${d['a_money']:,.0f}  B money: ${d['b_money']:,.0f}")
    print(f"  A market: {d['a_market']}")
    print(f"  B market: {d['b_market']}")
    
    # Identify what changed
    a_sells = [o for o in d['a_market'] if isinstance(o, list) and len(o) > 2 and o[0] == "SELL"]
    b_sells = [o for o in d['b_market'] if isinstance(o, list) and len(o) > 2 and o[0] == "SELL"]
    a_buys = [o for o in d['a_market'] if isinstance(o, list) and len(o) > 2 and o[0] == "BUY_PRODUCT"]
    b_buys = [o for o in d['b_market'] if isinstance(o, list) and len(o) > 2 and o[0] == "BUY_PRODUCT"]
    
    print(f"  A: {len(a_sells)} sells, {len(a_buys)} buys")
    print(f"  B: {len(b_sells)} sells, {len(b_buys)} buys")
    
    # Show what frontload changed
    if a_sells != b_sells or a_buys != b_buys:
        a_items = [(o[0], o[1], int(o[2])) for o in d['a_market'] if isinstance(o, list) and len(o) > 2]
        b_items = [(o[0], o[1], int(o[2])) for o in d['b_market'] if isinstance(o, list) and len(o) > 2]
        if a_items != b_items:
            print(f"  A sequence: {a_items}")
            print(f"  B sequence: {b_items}")
