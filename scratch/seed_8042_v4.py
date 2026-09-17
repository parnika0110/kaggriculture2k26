"""Trace full-game route changes on seed 8042 to find where $39K gap originates."""
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
_ROUTE_LOG = []
_MONEY_LOG = []
_orig_act = _IMPL.chassis.act
def _traced_act(observation, configuration=None):
    result = _orig_act(observation, configuration)
    player = observation.get('player', 0) if isinstance(observation, dict) else 0
    step = observation.get('step', 0) if isinstance(observation, dict) else 0
    if player == 0:
        st = _IMPL.chassis.players.get(0, {})
        route = st.get('route', None)
        money = observation.get('farms', [{}])[0].get('money', 0) if isinstance(observation, dict) else 0
        _ROUTE_LOG.append({'step': step, 'route': route})
        _MONEY_LOG.append({'step': step, 'money': money})
    return result
_IMPL.chassis.act = _traced_act
"""
    source = source.rstrip() + '\n' + hook + '\n'
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def main():
    print("=" * 70)
    print(f"SEED {SEED}: FULL-GAME ROUTE TRACE")
    print("=" * 70)
    
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        route_log = ns.get('_ROUTE_LOG', [])
        money_log = ns.get('_MONEY_LOG', [])
        
        print(f"\n[{variant.upper()}] Score: ${score:,.0f}")
        
        # Find route changes
        prev_route = None
        changes = []
        for e in route_log:
            if e['route'] != prev_route:
                changes.append(e)
                prev_route = e['route']
        
        print(f"  Route changes ({len(changes)} total):")
        for e in changes:
            # Find money at this step
            money_entry = next((m for m in money_log if m['step'] == e['step']), None)
            money = money_entry['money'] if money_entry else 0
            day = e['step'] // 24
            hour = e['step'] % 24
            print(f"    Step {e['step']:>3} (day {day}, hour {hour:>2}): route {e['route']}  money=${money:,.0f}")
        
        # Show money at key milestones
        print(f"\n  Money at key milestones:")
        milestones = [0, 24, 48, 72, 120, 168, 240, 360, 480, 600, 720]
        for step in milestones:
            entry = next((m for m in money_log if m['step'] == step), None)
            if entry:
                day = step // 24
                print(f"    Step {step:>3} (day {day:>2}): ${entry['money']:>10,.0f}")
    
    # Direct comparison of route changes
    print(f"\n{'='*70}")
    print("ROUTE CHANGE COMPARISON")
    print(f"{'='*70}")
    
    logs = {}
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        logs[variant] = ns.get('_ROUTE_LOG', [])
    
    # Compare routes at each step
    print(f"\n{'Step':>5} {'Day':>4} {'Hour':>5} {'C9 Route':>10} {'Orig Route':>12} {'Same?':>6}")
    print("-" * 50)
    for step in range(0, 720, 24):  # Check once per day
        c9_entry = next((e for e in logs['c9'] if e['step'] == step), None)
        orig_entry = next((e for e in logs['original'] if e['step'] == step), None)
        if c9_entry and orig_entry:
            same = c9_entry['route'] == orig_entry['route']
            day = step // 24
            hour = step % 24
            print(f"{step:>5} {day:>4} {hour:>5} {str(c9_entry['route']):>10} {str(orig_entry['route']):>12} {'YES' if same else 'NO':>6}")
    
    # Find first divergence
    prev_same = True
    for step in range(720):
        c9_entry = next((e for e in logs['c9'] if e['step'] == step), None)
        orig_entry = next((e for e in logs['original'] if e['step'] == step), None)
        if c9_entry and orig_entry:
            same = c9_entry['route'] == orig_entry['route']
            if not same and prev_same:
                day = step // 24
                hour = step % 24
                print(f"\n  FIRST ROUTE DIVERGENCE at step {step} (day {day}, hour {hour})")
                print(f"    C9 route: {c9_entry['route']}")
                print(f"    Original route: {orig_entry['route']}")
                break
            prev_same = same


if __name__ == "__main__":
    main()
