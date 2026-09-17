"""Focused 5-seed investigation: shop selection, divergence, and root cause."""
import sys, time, statistics
sys.path.insert(0, '.')

with open('submission_v43c9.py', 'r', encoding='utf-8-sig') as f:
    code = f.read()

# Build C9 agent
ns = {}
exec(compile(code, '<c9>', 'exec'), ns)
c9 = ns['agent']

# Build Original agent (uniform wheat flip on ALL routes)
i = code.find("_PIPE3_BAKERY_ROUTES")
s = code.rfind("\n", 0, i)
e = code.find("del _p3_rid,_p3_tape", i)
n = code.find("\n", e) + 1
r = "\n_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]\nfor _r42_tape in _ROUTES.values():\n    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])\n"
ns2 = {}
exec(compile(code[:s] + r + code[n:], '<orig>', 'exec'), ns2)
orig = ns2['agent']

from kaggle_environments import make

def run_self(agent_fn, seed):
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.run([agent_fn, agent_fn])
    return float(env.state[0]['reward'] or 0)

def run_h2h(p0, p1, seed):
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.run([p0, p1])
    return float(env.state[0]['reward'] or 0), float(env.state[1]['reward'] or 0)

def run_traced(agent_fn, seed):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed, "episodeSteps": 720}, debug=False)
    env.agents = [agent_fn, agent_fn]
    env.reset()
    trace = []
    while not env.done:
        obs = env.state[0]['observation']
        trace.append({
            'step': obs.get('step', 0),
            'day': obs.get('day', 0),
            'hour': obs.get('hour', 0),
            'shops': list(obs.get('town', {}).get('unlocked_shops', [])),
            'money': obs.get('farms', [{}])[0].get('money', 0),
            'prices': dict(obs.get('market', {}).get('prices', {})),
        })
        env.step([{}, {}])
    return trace, float(env.state[0]['reward'] or 0)

SEEDS = [0, 5, 7]

# === PHASE 1: Self-play performance ===
print("=" * 70)
print("PHASE 1: Self-play (independent performance)")
print("=" * 70)
c9s, os_ = [], []
for seed in SEEDS:
    t0 = time.time()
    sc = run_self(c9, seed)
    so = run_self(orig, seed)
    dt = time.time() - t0
    c9s.append(sc); os_.append(so)
    w = "C9" if sc > so else ("O" if so > sc else "T")
    print(f"  S{seed}: C9=${sc:>9,.0f} O=${so:>9,.0f} d=${sc-so:>+9,.0f} {w}  ({dt:.0f}s)")

print(f"\n  C9  mean=${statistics.mean(c9s):>10,.0f}  O mean=${statistics.mean(os_):>10,.0f}")
print(f"  C9  min =${min(c9s):>10,.0f}  O min =${min(os_):>10,.0f}")
print(f"  C9  max =${max(c9s):>10,.0f}  O max =${max(os_):>10,.0f}")

# === PHASE 2: H2H performance ===
print("\n" + "=" * 70)
print("PHASE 2: H2H (C9=P0 vs Orig=P1, same seed)")
print("=" * 70)
h2h_c, h2h_o = [], []
for seed in SEEDS:
    t0 = time.time()
    sc, so = run_h2h(c9, orig, seed)
    dt = time.time() - t0
    h2h_c.append(sc); h2h_o.append(so)
    w = "C9" if sc > so else ("O" if so > sc else "T")
    print(f"  S{seed}: C9=${sc:>9,.0f} O=${so:>9,.0f} d=${sc-so:>+9,.0f} {w}  ({dt:.0f}s)")

c9w = sum(1 for a,b in zip(h2h_c,h2h_o) if a>b)
print(f"\n  C9 wins {c9w}/{len(SEEDS)}, mean diff=${statistics.mean(h2h_c)-statistics.mean(h2h_o):>+10,.0f}")

# === PHASE 3: Traces for key seeds ===
print("\n" + "=" * 70)
print("PHASE 3: Divergence traces")
print("=" * 70)

for seed in SEEDS[:3]:  # Just first 3
    print(f"\n--- Seed {seed}: tracing C9 self-play ---")
    t0 = time.time()
    trace_c9, sc9 = run_traced(c9, seed)
    trace_o, so = run_traced(orig, seed)
    print(f"  Scores: C9=${sc9:,.0f} O=${so:,.0f} ({time.time()-t0:.0f}s)")
    
    # Find first divergence
    fd = None
    for idx in range(min(len(trace_c9), len(trace_o))):
        if abs(trace_c9[idx]['money'] - trace_o[idx]['money']) > 0.5:
            fd = idx
            break
    
    if fd is not None:
        print(f"  First divergence: step {fd}")
        for j in range(max(0, fd-1), min(len(trace_c9), fd+6)):
            tc = trace_c9[j]; to = trace_o[j]
            d = tc['money'] - to['money']
            m = " <--" if j == fd else ""
            shops_ok = tc['shops'] == to['shops']
            print(f"    S{j:>3} d{tc['day']}h{tc['hour']}: C9=${tc['money']:>9,.0f} O=${to['money']:>9,.0f} d=${d:>+9,.0f} {'OK' if shops_ok else 'SHOPS DIFF'}{m}")
    else:
        print("  No divergence!")
    
    # Shop timeline
    print("  Shops:")
    last = []
    for idx in range(len(trace_c9)):
        tc = trace_c9[idx]; to = trace_o[idx]
        if tc['hour'] == 0 and tc['shops'] != last:
            ok = tc['shops'] == to['shops']
            print(f"    Day {tc['day']:>2}: {tc['shops']} {'SAME' if ok else 'DIFF'}")
            last = list(tc['shops'])
    
    # Key prices
    print("  Prices at day boundaries:")
    for idx in range(len(trace_c9)):
        if trace_c9[idx]['hour'] == 0 and trace_c9[idx]['day'] <= 3:
            tc = trace_c9[idx]; to = trace_o[idx]
            print(f"    Day {tc['day']}: C9 WHEAT={tc['prices'].get('WHEAT',0)} O WHEAT={to['prices'].get('WHEAT',0)} "
                  f"C9 MILK={tc['prices'].get('MILK',0)} O MILK={to['prices'].get('MILK',0)} "
                  f"C9 WOOL={tc['prices'].get('WOOL',0)} O WOOL={to['prices'].get('WOOL',0)}")
