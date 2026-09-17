"""Phase 1-2: Trace seed-7 failure mode between C9 and Original V43."""
import json, copy, sys, os, time

sys.path.insert(0, '.')

def load_agent_code():
    with open('submission_v43c9.py', 'r', encoding='utf-8-sig') as f:
        return f.read()

def make_c9_agent(code):
    ns = {}
    exec(compile(code, '<c9>', 'exec'), ns)
    return ns['agent']

def make_original_agent(code):
    """Replace C9 pipe-3 with R42 wheat flip (uniform flip on ALL routes)."""
    idx_start = code.find("_PIPE3_BAKERY_ROUTES")
    line_start = code.rfind("\n", 0, idx_start)
    idx_end = code.find("del _p3_rid,_p3_tape", idx_start)
    line_end = code.find("\n", idx_end) + 1
    
    r42 = """
# R42: Original V43 wheat flip on ALL routes
_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
for _r42_tape in _ROUTES.values():
    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])
"""
    new_code = code[:line_start] + r42 + code[line_end:]
    ns = {}
    exec(compile(new_code, '<original>', 'exec'), ns)
    return ns['agent']

def run_game(agent_fn, seed):
    from kaggle_environments import make
    env = make("kaggriculture", debug=False)
    env.run([agent_fn, agent_fn])
    return float(env.state[0]['reward'] or 0), float(env.state[1]['reward'] or 0)

def run_game_traced(agent_fn, seed):
    """Run game step-by-step, capturing observations at each step."""
    from kaggle_environments import make
    env = make("kaggriculture", debug=False)
    configs = {"seed": seed, "episodeSteps": 720}
    env.reset(configs=configs)
    env.set_agents([agent_fn, agent_fn])
    
    trace = []
    for step in range(720):
        obs = env.state[0]['observation']
        shops = list(obs.get('town', {}).get('unlocked_shops', []))
        prices = dict(obs.get('market', {}).get('prices', {}))
        money0 = obs.get('farms', [{}])[0].get('money', 0)
        money1 = obs.get('farms', [{}])[1].get('money', 0)
        
        trace.append({
            'step': step,
            'day': obs.get('day', 0),
            'hour': obs.get('hour', 0),
            'shops': shops,
            'wheat_price': prices.get('WHEAT', 0),
            'milk_price': prices.get('MILK', 0),
            'wool_price': prices.get('WOOL', 0),
            'money_p0': money0,
            'money_p1': money1,
        })
        
        if all(env.done):
            break
        env.step([{}, {}])
    
    score0 = float(env.state[0]['reward'] or 0)
    score1 = float(env.state[1]['reward'] or 0)
    return trace, score0, score1

# === MAIN ===
print("Loading agent code...")
code = load_agent_code()
print(f"  Code: {len(code)} chars")

print("Building agents...")
c9_agent = make_c9_agent(code)
orig_agent = make_original_agent(code)
print("  Done.\n")

# === PART 1: Reproduce seed-7 failure ===
print("=" * 70)
print("PART 1: Reproduce seed-7 failure")
print("=" * 70)

for seed in [0, 7, 42]:
    s_c9_0, s_c9_1 = run_game(c9_agent, seed)
    s_orig_0, s_orig_1 = run_game(orig_agent, seed)
    print(f"  Seed {seed:>2}: C9=[{s_c9_0:>9,.0f}, {s_c9_1:>9,.0f}]  Orig=[{s_orig_0:>9,.0f}, {s_orig_1:>9,.0f}]  P0 diff={s_c9_0-s_orig_0:>+9,.0f}")

# === PART 2: 10-seed sweep ===
print("\n" + "=" * 70)
print("PART 2: Seeds 0-9 head-to-head (same seed, both agents as P0)")
print("=" * 70)

print(f"\n{'Seed':>4} | {'C9 P0':>10} | {'Orig P0':>10} | {'Diff':>10} | {'C9 P1':>10} | {'Orig P1':>10}")
print(f"{'-'*4}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

for seed in range(10):
    c9_0, c9_1 = run_game(c9_agent, seed)
    o_0, o_1 = run_game(orig_agent, seed)
    print(f"{seed:>4} | ${c9_0:>8,.0f} | ${o_0:>8,.0f} | ${c9_0-o_0:>+8,.0f} | ${c9_1:>8,.0f} | ${o_1:>8,.0f}")

# === PART 3: Trace seed 7 step-by-step ===
print("\n" + "=" * 70)
print("PART 3: Seed-7 step-by-step trace")
print("=" * 70)

trace_c9, sc9_0, sc9_1 = run_game_traced(c9_agent, 7)
trace_orig, so_0, so_1 = run_game_traced(orig_agent, 7)

print(f"\nFinal scores: C9 P0=${sc9_0:,.0f}  Orig P0=${so_0:,.0f}  Gap=${so_0-sc9_0:,.0f}")

# Find divergence point
print("\n--- Divergence analysis ---")
first_diff_step = None
for i in range(min(len(trace_c9), len(trace_orig))):
    d = trace_c9[i]['money_p0'] - trace_orig[i]['money_p0']
    if abs(d) > 0.5:
        first_diff_step = i
        break

if first_diff_step is not None:
    print(f"First money divergence at step {first_diff_step} (day {trace_c9[first_diff_step]['day']}, hour {trace_c9[first_diff_step]['hour']})")
    # Show context
    for s in range(max(0, first_diff_step - 2), min(len(trace_c9), first_diff_step + 10)):
        tc = trace_c9[s]
        to = trace_orig[s]
        d = tc['money_p0'] - to['money_p0']
        marker = " <-- DIVERGENCE" if s == first_diff_step else ""
        shops_match = "OK" if tc['shops'] == to['shops'] else "DIFF"
        print(f"  Step {s:>3} d{tc['day']}h{tc['hour']}: C9=${tc['money_p0']:>9,.0f} Orig=${to['money_p0']:>9,.0f} Diff=${d:>+9,.0f} Shops:{shops_match}{marker}")
else:
    print("No divergence found in money!")

# Show shop unlock timeline
print("\n--- Shop unlock timeline (seed 7) ---")
last_shops_c9 = []
last_shops_orig = []
for i in range(len(trace_c9)):
    tc = trace_c9[i]
    to = trace_orig[i]
    if tc['hour'] == 0 and tc['shops'] != last_shops_c9:
        match = "SAME" if tc['shops'] == to['shops'] else "DIFF"
        print(f"  Day {tc['day']:>2} (step {i:>3}): C9={tc['shops']}")
        if match == "DIFF":
            print(f"           Orig={to['shops']}  *** DIFFERENT ***")
        last_shops_c9 = tc['shops']
        last_shops_orig = to['shops']

# Show money at key milestones
print("\n--- Money at day boundaries (seed 7) ---")
print(f"{'Day':>4} | {'C9 P0':>10} | {'Orig P0':>10} | {'Diff':>10}")
print(f"{'-'*4}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")
for i in range(len(trace_c9)):
    tc = trace_c9[i]
    to = trace_orig[i]
    if tc['hour'] == 0:
        d = tc['money_p0'] - to['money_p0']
        print(f"{tc['day']:>4} | ${tc['money_p0']:>8,.0f} | ${to['money_p0']:>8,.0f} | ${d:>+8,.0f}")
