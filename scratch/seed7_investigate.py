"""Investigate seed 7: what triggers the compounding failure?"""
import json, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

route_data = load_route_data()

def build_tracing_agent(variant):
    source = load_notebook_agent().replace('\r\n', '\n')
    if variant == 'original':
        old = """_PIPE3_BAKERY_ROUTES={101,103,104,105,106,107,108,109,111,119,120}
_PIPE3_MINIMAL=[['BUY_PRODUCT','WHEAT',5]]
_PIPE3_WHEAT=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
_PIPE3_STEP2_MIN=[['HIRE'],['HIRE'],['HIRE'],['HIRE'],['HIRE'],['BUY_ANIMAL','COW',2],['BUY_ANIMAL','SHEEP',2]]
for _p3_rid,_p3_tape in _ROUTES.items():
    if _p3_rid in _PIPE3_BAKERY_ROUTES:
        _p3_tape[0]=dict(_p3_tape[0],market=[list(o) for o in _PIPE3_WHEAT])
    else:
        _p3_tape[0]=dict(_p3_tape[0],market=[list(o) for o in _PIPE3_MINIMAL])
        _p3_tape[1]=dict(_p3_tape[1],market=[list(o) for o in _PIPE3_STEP2_MIN])
del _p3_rid,_p3_tape"""
        new = """_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
for _r42_tape in _ROUTES.values():
    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])
del _r42_tape"""
        source = source.replace(old, new)
    
    hook = """
_LOG = []
_orig_act = _IMPL.chassis.act
def _traced_act(observation, configuration=None):
    result = _orig_act(observation, configuration)
    player = observation.get('player', 0) if isinstance(observation, dict) else 0
    step = observation.get('step', 0) if isinstance(observation, dict) else 0
    if player == 0:
        st = _IMPL.chassis.players.get(0, {})
        route = st.get('route', None)
        money = observation.get('farms', [{}])[0].get('money', 0) if isinstance(observation, dict) else 0
        prices = observation.get('market', {}).get('prices', {}) if isinstance(observation, dict) else {}
        town = observation.get('town', {}).get('unlocked_shops', []) if isinstance(observation, dict) else []
        _LOG.append({'step': step, 'route': route, 'money': money, 'prices': dict(prices), 'shops': list(town)})
    return result
_IMPL.chassis.act = _traced_act
"""
    source = source.rstrip() + '\n' + hook + '\n'
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def analyze_seed(seed, label=""):
    print(f"\n{'='*70}")
    print(f"SEED {seed} {label}")
    print(f"{'='*70}")
    
    logs = {}
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        logs[variant] = ns.get('_LOG', [])
        print(f"\n[{variant.upper()}] Score: ${score:,.0f}")
    
    # Compare shop unlocks
    print(f"\n--- Shop unlock comparison ---")
    c9_shops = set()
    orig_shops = set()
    for e in logs['c9']:
        for s in e.get('shops', []):
            c9_shops.add(s)
    for e in logs['original']:
        for s in e.get('shops', []):
            orig_shops.add(s)
    
    print(f"  C9 shops: {sorted(c9_shops)}")
    print(f"  Orig shops: {sorted(orig_shops)}")
    print(f"  Same? {c9_shops == orig_shops}")
    
    # Compare route changes
    print(f"\n--- Route changes ---")
    c9_routes = [(e['step'], e['route']) for e in logs['c9'] if e['route'] != (logs['c9'][logs['c9'].index(e)-1]['route'] if logs['c9'].index(e) > 0 else None)]
    orig_routes = [(e['step'], e['route']) for e in logs['original'] if e['route'] != (logs['original'][logs['original'].index(e)-1]['route'] if logs['original'].index(e) > 0 else None)]
    
    # Simplify: just show route at each day boundary
    print(f"  {'Day':>4} {'C9 Route':>10} {'Orig Route':>12} {'Same?':>6}")
    for day in range(30):
        step = day * 24
        c9_r = next((e['route'] for e in logs['c9'] if e['step'] == step), None)
        orig_r = next((e['route'] for e in logs['original'] if e['step'] == step), None)
        if c9_r is not None and orig_r is not None:
            same = c9_r == orig_r
            print(f"  {day:>4} {str(c9_r):>10} {str(orig_r):>12} {'YES' if same else 'NO':>6}")
    
    # Compare money at key points
    print(f"\n--- Money comparison ---")
    print(f"  {'Step':>5} {'Day':>4} {'C9$':>10} {'Orig$':>10} {'Diff':>10}")
    for step in [0, 24, 48, 72, 120, 168, 216, 240, 264, 360, 480, 600, 720]:
        c9_e = next((e for e in logs['c9'] if e['step'] == step), None)
        orig_e = next((e for e in logs['original'] if e['step'] == step), None)
        if c9_e and orig_e:
            diff = c9_e['money'] - orig_e['money']
            day = step // 24
            print(f"  {step:>5} {day:>4} ${c9_e['money']:>9,.0f} ${orig_e['money']:>9,.0f} ${diff:>+9,.0f}")


from notebook_analysis import load_notebook_agent

# Test seed 7 (failure) vs seed 0 (normal)
analyze_seed(7, "(FAILURE SEED)")
analyze_seed(0, "(NORMAL SEED)")
