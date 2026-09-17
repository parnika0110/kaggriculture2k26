"""Trace C9 vs Original on multiple seeds."""
import json, copy, sys, os, time, statistics

sys.path.insert(0, '.')

def load_agent_code():
    with open('submission_v43c9.py', 'r', encoding='utf-8-sig') as f:
        return f.read()

def make_c9_agent(code):
    ns = {}
    exec(compile(code, '<c9>', 'exec'), ns)
    return ns['agent']

def make_original_agent(code):
    idx_start = code.find("_PIPE3_BAKERY_ROUTES")
    line_start = code.rfind("\n", 0, idx_start)
    idx_end = code.find("del _p3_rid,_p3_tape", idx_start)
    line_end = code.find("\n", idx_end) + 1
    
    r42 = """
_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
for _r42_tape in _ROUTES.values():
    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])
"""
    new_code = code[:line_start] + r42 + code[line_end:]
    ns = {}
    exec(compile(new_code, '<original>', 'exec'), ns)
    return ns['agent']

def run_h2h(p0_agent, p1_agent, seed):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.run([p0_agent, p1_agent])
    return float(env.state[0]['reward'] or 0), float(env.state[1]['reward'] or 0)

def run_self(agent_fn, seed):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.run([agent_fn, agent_fn])
    return float(env.state[0]['reward'] or 0)

def run_traced(agent_fn, seed):
    """Self-play, capturing observations."""
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.agents = [agent_fn, agent_fn]
    env.reset()
    
    trace = []
    while not all(env.done):
        obs = env.state[0]['observation']
        shops = list(obs.get('town', {}).get('unlocked_shops', []))
        prices = dict(obs.get('market', {}).get('prices', {}))
        farms = obs.get('farms', [{}])
        money0 = farms[0].get('money', 0) if len(farms) > 0 else 0
        shed = dict(obs.get('private', {}).get('shed', {}))
        seeds = dict(obs.get('private', {}).get('seeds', {}))
        
        trace.append({
            'step': obs.get('step', 0),
            'day': obs.get('day', 0),
            'hour': obs.get('hour', 0),
            'shops': shops,
            'prices': prices,
            'money': money0,
            'shed': shed,
            'seeds': seeds,
        })
        env.step([{}, {}])
    
    score = float(env.state[0]['reward'] or 0)
    return trace, score

# === MAIN ===
print("Loading agent code...", flush=True)
code = load_agent_code()
print(f"  Code: {len(code)} chars", flush=True)

print("Building agents...", flush=True)
c9_agent = make_c9_agent(code)
orig_agent = make_original_agent(code)
print("  Done.", flush=True)

# === 30-seed H2H benchmark ===
print("\n" + "=" * 70)
print("30-SEED H2H BENCHMARK (C9=P0, Original=P1)")
print("=" * 70)

c9_wins = 0
orig_wins = 0
c9_scores = []
orig_scores = []

for seed in range(30):
    s_c9, s_orig = run_h2h(c9_agent, orig_agent, seed)
    c9_scores.append(s_c9)
    orig_scores.append(s_orig)
    if s_c9 > s_orig:
        c9_wins += 1
        winner = "C9"
    elif s_orig > s_c9:
        orig_wins += 1
        winner = "Orig"
    else:
        winner = "TIE"
    print(f"  Seed {seed:>2}: C9=${s_c9:>9,.0f}  Orig=${s_orig:>9,.0f}  Diff=${s_c9-s_orig:>+9,.0f}  {winner}")

print(f"\nSUMMARY: C9 wins {c9_wins}/30, Original wins {orig_wins}/30, Ties {30-c9_wins-orig_wins}/30")
print(f"C9   mean=${statistics.mean(c9_scores):>10,.0f}  median=${statistics.median(c9_scores):>10,.0f}")
print(f"Orig mean=${statistics.mean(orig_scores):>10,.0f}  median=${statistics.median(orig_scores):>10,.0f}")
print(f"C9 mean advantage: ${statistics.mean(c9_scores)-statistics.mean(orig_scores):>+10,.0f}")

# === Also benchmark self-play (independent performance) ===
print("\n" + "=" * 70)
print("30-SEED SELF-PLAY BENCHMARK (independent performance)")
print("=" * 70)

c9_self = []
orig_self = []
c9_self_wins = 0

for seed in range(30):
    s_c9 = run_self(c9_agent, seed)
    s_orig = run_self(orig_agent, seed)
    c9_self.append(s_c9)
    orig_self.append(s_orig)
    if s_c9 > s_orig:
        c9_self_wins += 1
        winner = "C9"
    elif s_orig > s_c9:
        winner = "Orig"
    else:
        winner = "TIE"
    print(f"  Seed {seed:>2}: C9=${s_c9:>9,.0f}  Orig=${s_orig:>9,.0f}  Diff=${s_c9-s_orig:>+9,.0f}  {winner}")

print(f"\nSUMMARY: C9 better {c9_self_wins}/30 seeds")
print(f"C9   mean=${statistics.mean(c9_self):>10,.0f}  median=${statistics.median(c9_self):>10,.0f}")
print(f"Orig mean=${statistics.mean(orig_self):>10,.0f}  median=${statistics.median(orig_self):>10,.0f}")
print(f"C9 mean advantage: ${statistics.mean(c9_self)-statistics.mean(orig_self):>+10,.0f}")

# === Trace worst seeds (self-play) ===
print("\n" + "=" * 70)
print("DETAILED TRACES: 3 WORST SEEDS FOR C9 (self-play)")
print("=" * 70)

worst = sorted(range(30), key=lambda s: c9_self[s] - orig_self[s])[:3]
print(f"Worst seeds: {worst}")

for seed in worst:
    trace_c9, sc9 = run_traced(c9_agent, seed)
    trace_orig, so = run_traced(orig_agent, seed)
    
    print(f"\n--- Seed {seed}: C9=${sc9:,.0f}  Orig=${so:,.0f}  Gap=${sc9-so:>+,.0f} ---")
    
    # Find first divergence
    first_diff = None
    for i in range(min(len(trace_c9), len(trace_orig))):
        d = trace_c9[i]['money'] - trace_orig[i]['money']
        if abs(d) > 0.5:
            first_diff = i
            break
    
    if first_diff is not None:
        print(f"  First money divergence: step {first_diff}")
        for s in range(max(0, first_diff - 2), min(len(trace_c9), first_diff + 8)):
            tc = trace_c9[s]
            to = trace_orig[s]
            d = tc['money'] - to['money']
            shops_ok = tc['shops'] == to['shops']
            marker = " <--" if s == first_diff else ""
            print(f"    Step {s:>3} d{tc['day']}h{tc['hour']}: C9=${tc['money']:>9,.0f} Orig=${to['money']:>9,.0f} Diff=${d:>+9,.0f} Shops:{'OK' if shops_ok else 'DIFF'}{marker}")
    else:
        print("  No money divergence!")
    
    # Shop timeline
    print("  Shop unlocks:")
    last = []
    for i in range(len(trace_c9)):
        tc = trace_c9[i]
        to = trace_orig[i]
        if tc['hour'] == 0 and tc['shops'] != last:
            shops_ok = tc['shops'] == to['shops']
            print(f"    Day {tc['day']:>2}: {tc['shops']} {'SAME' if shops_ok else 'DIFFERENT'}")
            last = list(tc['shops'])

# === Trace 3 best seeds for C9 ===
print("\n" + "=" * 70)
print("DETAILED TRACES: 3 BEST SEEDS FOR C9 (self-play)")
print("=" * 70)

best = sorted(range(30), key=lambda s: c9_self[s] - orig_self[s], reverse=True)[:3]
print(f"Best seeds: {best}")

for seed in best:
    trace_c9, sc9 = run_traced(c9_agent, seed)
    trace_orig, so = run_traced(orig_agent, seed)
    
    print(f"\n--- Seed {seed}: C9=${sc9:,.0f}  Orig=${so:,.0f}  Gap=${sc9-so:>+,.0f} ---")
    
    first_diff = None
    for i in range(min(len(trace_c9), len(trace_orig))):
        d = trace_c9[i]['money'] - trace_orig[i]['money']
        if abs(d) > 0.5:
            first_diff = i
            break
    
    if first_diff is not None:
        print(f"  First money divergence: step {first_diff}")
        for s in range(max(0, first_diff - 2), min(len(trace_c9), first_diff + 8)):
            tc = trace_c9[s]
            to = trace_orig[s]
            d = tc['money'] - to['money']
            shops_ok = tc['shops'] == to['shops']
            marker = " <--" if s == first_diff else ""
            print(f"    Step {s:>3} d{tc['day']}h{tc['hour']}: C9=${tc['money']:>9,.0f} Orig=${to['money']:>9,.0f} Diff=${d:>+9,.0f} Shops:{'OK' if shops_ok else 'DIFF'}{marker}")
    else:
        print("  No money divergence!")
