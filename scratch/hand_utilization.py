"""Trace hand utilization across a full V43+C9 game.

For each hand, track: hire step, actions, PASS/idle, responsibilities.
"""
import json, sys
sys.path.insert(0, '.')

base_globals = {}
exec(open('submission.py', encoding='utf-8').read(), base_globals)
base_agent = base_globals['agent']

from kaggle_environments import make

CONFIG = {"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}

def trace_game(seed):
    """Run one game and trace all hand actions."""
    cfg = dict(CONFIG); cfg["seed"] = seed
    env = make("kaggriculture", debug=True, configuration=cfg)
    trainer = env.train([None, "starter"])
    obs = trainer.reset()
    
    # Per-hand tracking
    hands = {}  # hand_idx -> {hire_step, actions: [], pass_count, active_steps}
    
    step = 0
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = base_agent(obs_json)
        
        # Get current hand count
        n_hands = len(obs["farms"][0].get("hands", []))
        
        # Track new hands (hired this step via market orders)
        market = action.get("market", [])
        for o in market:
            if isinstance(o, list) and len(o) > 0 and o[0] == "HIRE":
                # New hand will appear next step
                pass
        
        # Track farmer action
        farmer_action = action.get("farmer", ["PASS"])
        
        # Track hand actions
        hands_actions = action.get("hands", [])
        for i, hand_act in enumerate(hands_actions):
            if i not in hands:
                hands[i] = {
                    "hire_step": step,
                    "actions": [],
                    "pass_count": 0,
                    "active_steps": 0,
                    "action_types": {},
                }
            hands[i]["active_steps"] += 1
            act = hand_act if isinstance(hand_act, list) else ["PASS"]
            op = act[0] if act else "PASS"
            hands[i]["actions"].append({"step": step, "action": act})
            hands[i]["action_types"][op] = hands[i]["action_types"].get(op, 0) + 1
            if op == "PASS" or not act:
                hands[i]["pass_count"] += 1
        
        obs, reward, done, info = trainer.step(action)
        step += 1
    
    return hands, reward, step

# Run on seed 0 for detailed analysis
print("=" * 80)
print("HAND UTILIZATION ANALYSIS (seed 0)")
print("=" * 80)

hands, reward, total_steps = trace_game(0)
print(f"Final score: ${reward:,.0f}")
print(f"Total steps: {total_steps}")
print(f"Total hands: {len(hands)}")

print(f"\n{'hand':>4s} | {'hire_step':>9s} | {'active':>6s} | {'PASS':>5s} | {'active%':>7s} | action types")
print("-" * 100)
for i in sorted(hands.keys()):
    h = hands[i]
    active_pct = h["active_steps"] / total_steps * 100
    pass_pct = h["pass_count"] / h["active_steps"] * 100 if h["active_steps"] > 0 else 0
    action_str = ", ".join(f"{k}:{v}" for k, v in sorted(h["action_types"].items(), key=lambda x: -x[1]))
    print(f"{i:4d} | {h['hire_step']:9d} | {h['active_steps']:6d} | {h['pass_count']:5d} | {active_pct:6.1f}% | {action_str}")

# Summary
total_actions = sum(h["active_steps"] for h in hands.values())
total_pass = sum(h["pass_count"] for h in hands.values())
total_meaningful = total_actions - total_pass
print(f"\nTotal hand actions: {total_actions}")
print(f"Total PASS: {total_pass} ({total_pass/total_actions*100:.1f}%)")
print(f"Total meaningful: {total_meaningful} ({total_meaningful/total_actions*100:.1f}%)")

# Identify the least critical hand
# The hand with the most PASS and fewest unique action types is least critical
print(f"\n{'='*80}")
print("LEAST CRITICAL HAND ANALYSIS")
print("=" * 80)
for i in sorted(hands.keys()):
    h = hands[i]
    unique_types = len(h["action_types"])
    meaningful = h["active_steps"] - h["pass_count"]
    print(f"Hand {i}: {h['pass_count']} PASS, {meaningful} meaningful, {unique_types} unique action types")

# Also check: which hands have the same action pattern?
print(f"\n{'='*80}")
print("HAND SIMILARITY (action type distribution)")
print("=" * 80)
for i in sorted(hands.keys()):
    h = hands[i]
    total = h["active_steps"]
    dist = {k: v/total for k, v in h["action_types"].items()}
    print(f"Hand {i}: {dist}")

# Run on 5 seeds to get average utilization
print(f"\n{'='*80}")
print("AVERAGE UTILIZATION ACROSS 5 SEEDS")
print("=" * 80)
all_hands = {}
for seed in range(5):
    hands, reward, total_steps = trace_game(seed)
    for i in sorted(hands.keys()):
        if i not in all_hands:
            all_hands[i] = {"pass_counts": [], "active_steps": [], "action_types": []}
        all_hands[i]["pass_counts"].append(hands[i]["pass_count"])
        all_hands[i]["active_steps"].append(hands[i]["active_steps"])
        all_hands[i]["action_types"].append(hands[i]["action_types"])

print(f"\n{'hand':>4s} | {'avg_active':>10s} | {'avg_PASS':>8s} | {'PASS%':>6s} | {'avg_meaningful':>14s}")
print("-" * 60)
for i in sorted(all_hands.keys()):
    h = all_hands[i]
    avg_active = sum(h["active_steps"]) / len(h["active_steps"])
    avg_pass = sum(h["pass_counts"]) / len(h["pass_counts"])
    pass_pct = avg_pass / avg_active * 100 if avg_active > 0 else 0
    avg_meaningful = avg_active - avg_pass
    print(f"{i:4d} | {avg_active:10.1f} | {avg_pass:8.1f} | {pass_pct:5.1f}% | {avg_meaningful:14.1f}")
