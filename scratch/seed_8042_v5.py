"""Trace compounding: find the critical point where small money gap becomes large."""
import json, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent

SEED = 8042
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
_STEP_LOG = []
_orig_act = _IMPL.chassis.act
def _traced_act(observation, configuration=None):
    result = _orig_act(observation, configuration)
    player = observation.get('player', 0) if isinstance(observation, dict) else 0
    step = observation.get('step', 0) if isinstance(observation, dict) else 0
    if player == 0:
        money = observation.get('farms', [{}])[0].get('money', 0) if isinstance(observation, dict) else 0
        private = observation.get('private', {}) if isinstance(observation, dict) else {}
        shed = private.get('shed', {})
        seeds = private.get('seeds', {})
        market = result.get('market', []) if isinstance(result, dict) else []
        _STEP_LOG.append({
            'step': step, 'money': money,
            'wheat': shed.get('WHEAT', 0), 'cow': shed.get('COW', 0), 'sheep': shed.get('SHEEP', 0),
            'melon_seed': seeds.get('MELON', 0), 'wheat_seed': seeds.get('WHEAT', 0),
            'market_orders': len(market),
        })
    return result
_IMPL.chassis.act = _traced_act
"""
    source = source.rstrip() + '\n' + hook + '\n'
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def main():
    print("=" * 70)
    print(f"SEED {SEED}: COMPOUNDING TRACE")
    print("=" * 70)
    
    logs = {}
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        logs[variant] = ns.get('_STEP_LOG', [])
        print(f"[{variant.upper()}] Score: ${score:,.0f}")
    
    # Find critical divergence points
    print(f"\n--- Money divergence over time ---")
    print(f"{'Step':>5} {'Day':>4} {'C9$':>10} {'Orig$':>10} {'Diff':>10} {'C9 Wheat':>9} {'Orig Wheat':>11} {'C9 Seeds':>9} {'Orig Seeds':>11}")
    print("-" * 90)
    
    prev_diff = 0
    for step in range(0, 720, 12):  # Check every 12 steps (half day)
        c9 = next((e for e in logs['c9'] if e['step'] == step), None)
        orig = next((e for e in logs['original'] if e['step'] == step), None)
        if c9 and orig:
            diff = c9['money'] - orig['money']
            day = step // 24
            # Only print if diff changed significantly
            if abs(diff - prev_diff) > 10 or step % 24 == 0 or step < 50:
                print(f"{step:>5} {day:>4} ${c9['money']:>9,.0f} ${orig['money']:>9,.0f} ${diff:>+9,.0f} {c9['wheat']:>9} {orig['wheat']:>11} {c9['melon_seed']:>9} {orig['melon_seed']:>11}")
                prev_diff = diff
    
    # Find the step where diff first exceeds thresholds
    print(f"\n--- Critical thresholds ---")
    thresholds = [10, 50, 100, 500, 1000, 5000, 10000, 20000, 30000]
    for t in thresholds:
        for step in range(720):
            c9 = next((e for e in logs['c9'] if e['step'] == step), None)
            orig = next((e for e in logs['original'] if e['step'] == step), None)
            if c9 and orig:
                diff = abs(c9['money'] - orig['money'])
                if diff >= t:
                    day = step // 24
                    hour = step % 24
                    print(f"  Diff > ${t:>6,}: step {step} (day {day}, hour {hour})")
                    break
    
    # Analyze wheat consumption in routes
    print(f"\n--- Wheat consumption analysis ---")
    source = load_notebook_agent().replace('\r\n', '\n')
    ns_routes = {'__builtins__': __builtins__}
    exec(compile(source, '<routes>', 'exec'), ns_routes)
    chassis = ns_routes['_IMPL'].chassis
    
    for route_id in [0, 12, 2]:
        if route_id not in chassis.routes:
            continue
        tape = chassis.routes[route_id]
        wheat_buys = 0
        wheat_sells = 0
        feed_count = 0
        for a in tape:
            if not isinstance(a, dict):
                continue
            for o in (a.get('market') or []):
                if not o or len(o) < 3:
                    continue
                if o[1] == 'WHEAT':
                    if o[0] == 'BUY_PRODUCT':
                        wheat_buys += o[2]
                    elif o[0] == 'SELL':
                        wheat_sells += o[2]
            # Count FEED actions (unit actions, not market)
            farmer = a.get('farmer', [])
            if farmer and farmer[0] == 'FEED':
                feed_count += 1
            for h in (a.get('hands') or []):
                if h and h[0] == 'FEED':
                    feed_count += 1
        
        print(f"  Route {route_id}: wheat_buys={wheat_buys} wheat_sells={wheat_sells} feed_actions={feed_count}")


if __name__ == "__main__":
    main()
