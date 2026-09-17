"""Find the REAL cause of seed 7's $20K gap: step-by-step comparison."""
import json, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')

SEED = 7

def build_agent(variant):
    with open('submission_v43c9.py', 'r', encoding='utf-8') as f:
        source = f.read().replace('\r\n', '\n')
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
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent']

from kaggle_environments import make

# Run both variants
logs = {}
for variant in ['c9', 'original']:
    agent_fn = build_agent(variant)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
    env.reset()
    
    step_log = []
    for step in range(719):
        obs = copy.deepcopy(env.state[0].observation)
        action = agent_fn(obs)
        
        # Capture state
        farms = obs.get('farms', [{}])[0]
        private = obs.get('private', {})
        shed = private.get('shed', {})
        seeds = private.get('seeds', {})
        money = farms.get('money', 0)
        day = obs.get('day', 0)
        hour = obs.get('hour', 0)
        shops = obs.get('town', {}).get('unlocked_shops', [])
        market = action.get('market', [])
        
        step_log.append({
            'step': step, 'day': day, 'hour': hour,
            'money': money, 'shops': list(shops),
            'wheat': shed.get('WHEAT', 0),
            'melon_seed': seeds.get('MELON', 0),
            'wheat_seed': seeds.get('WHEAT', 0),
            'market_orders': len(market),
            'market': [list(o) for o in market],
        })
        
        env.step([action, {"farmer": ["PASS"], "hands": [], "market": []}])
    
    logs[variant] = step_log
    score = env.steps[-1][0].reward
    print(f"[{variant.upper()}] Score: ${score:,.0f}")

# Compare step by step
print(f"\n{'='*70}")
print(f"STEP-BY-STEP COMPARISON (seed {SEED})")
print(f"{'='*70}")

# Find first divergence
for step in range(720):
    c9 = logs['c9'][step]
    orig = logs['original'][step]
    
    # Check for divergences
    diffs = []
    if c9['money'] != orig['money']:
        diffs.append(f"money: C9=${c9['money']:,.0f} Orig=${orig['money']:,.0f}")
    if c9['wheat'] != orig['wheat']:
        diffs.append(f"wheat: C9={c9['wheat']} Orig={orig['wheat']}")
    if c9['melon_seed'] != orig['melon_seed']:
        diffs.append(f"melon_seed: C9={c9['melon_seed']} Orig={orig['melon_seed']}")
    if c9['wheat_seed'] != orig['wheat_seed']:
        diffs.append(f"wheat_seed: C9={c9['wheat_seed']} Orig={orig['wheat_seed']}")
    if c9['market_orders'] != orig['market_orders']:
        diffs.append(f"market_orders: C9={c9['market_orders']} Orig={orig['market_orders']}")
    if c9['market'] != orig['market']:
        diffs.append(f"market: C9={c9['market']} Orig={orig['market']}")
    
    if diffs:
        print(f"\nStep {step} (day {c9['day']}, hour {c9['hour']}):")
        for d in diffs:
            print(f"  {d}")

# Show money at key milestones
print(f"\n{'='*70}")
print(f"MONEY AT KEY MILESTONES")
print(f"{'='*70}")
print(f"{'Step':>5} {'Day':>4} {'C9$':>10} {'Orig$':>10} {'Diff':>10}")
for step in [0, 24, 48, 72, 120, 168, 216, 240, 264, 360, 480, 600]:
    c9 = logs['c9'][step]
    orig = logs['original'][step]
    diff = c9['money'] - orig['money']
    print(f"{step:>5} {c9['day']:>4} ${c9['money']:>9,.0f} ${orig['money']:>9,.0f} ${diff:>+9,.0f}")

# Final scores
c9_score = logs['c9'][-1]['money']
orig_score = logs['original'][-1]['money']
print(f"\nFinal: C9=${c9_score:,.0f}  Orig=${orig_score:,.0f}  diff=${c9_score-orig_score:+,.0f}")
