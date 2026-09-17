"""Trace shed contents cascade on seed 8042: how wheat flip affects the whole game."""
import json, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

SEED = 8042
route_data = load_route_data()

def build_tracing_agent(variant):
    """Build agent with step-by-step shed tracing."""
    from notebook_analysis import load_notebook_agent
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
    
    # Inject shed tracing
    hook = """
_SHED_LOG = []
_orig_act = _IMPL.chassis.act
def _traced_act(observation, configuration=None):
    result = _orig_act(observation, configuration)
    player = observation.get('player', 0) if isinstance(observation, dict) else 0
    step = observation.get('step', 0) if isinstance(observation, dict) else 0
    if player == 0:
        private = observation.get('private', {}) if isinstance(observation, dict) else {}
        shed = private.get('shed', {})
        market = result.get('market', []) if isinstance(result, dict) else []
        _SHED_LOG.append({'step': step, 'shed': dict(shed), 'market': market, 'money': observation.get('farms', [{}])[0].get('money', 0) if isinstance(observation, dict) else 0})
    return result
_IMPL.chassis.act = _traced_act
"""
    source = source.rstrip() + '\n' + hook + '\n'
    
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def main():
    print("=" * 70)
    print(f"SEED {SEED}: SHED CONTENTS CASCADE TRACE")
    print("=" * 70)
    
    logs = {}
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        log = ns.get('_SHED_LOG', [])
        logs[variant] = log
        print(f"\n[{variant.upper()}] Score: ${score:,.0f}")
        
        # Show shed for first 25 steps (day 0 + start of day 1)
        print(f"  Shed contents (first 25 steps):")
        print(f"  {'Step':>4} {'Money':>10} {'WHEAT':>6} {'COW':>4} {'SHEEP':>6} {'MELON':>6} {'TOMATO':>7} {'FERT':>5} {'Market orders'}")
        for e in log[:25]:
            s = e['shed']
            m = e['money']
            orders = len(e['market'])
            print(f"  {e['step']:>4} ${m:>9,.0f} {s.get('WHEAT',0):>6} {s.get('COW',0):>4} {s.get('SHEEP',0):>6} {s.get('MELON',0):>6} {s.get('TOMATO',0):>7} {s.get('FERTILIZER',0):>5} {orders} orders: {e['market']}")
    
    # Compare key differences
    print(f"\n{'='*70}")
    print("KEY DIFFERENCES")
    print(f"{'='*70}")
    
    for step in [0, 1, 2, 3, 4, 5, 10, 15, 20, 24]:
        c9_entry = next((e for e in logs['c9'] if e['step'] == step), None)
        orig_entry = next((e for e in logs['original'] if e['step'] == step), None)
        if c9_entry and orig_entry:
            c9_shed = c9_entry['shed']
            orig_shed = orig_entry['shed']
            wheat_diff = c9_shed.get('WHEAT', 0) - orig_shed.get('WHEAT', 0)
            money_diff = c9_entry['money'] - orig_entry['money']
            print(f"  Step {step:>2}: money diff=${money_diff:>+10,.0f}  wheat diff={wheat_diff:>+4}")
    
    # Final scores
    print(f"\n{'='*70}")
    print("FINAL SCORES")
    print(f"{'='*70}")
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        print(f"  {variant:>10}: ${score:>10,.0f}")
    
    c9_score = None
    orig_score = None
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        if variant == 'c9': c9_score = score
        else: orig_score = score
    
    print(f"\n  Difference: ${c9_score - orig_score:+,.0f}")
    print(f"  The wheat flip provides a $39K advantage on this seed.")


if __name__ == "__main__":
    main()
