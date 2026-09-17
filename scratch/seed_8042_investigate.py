"""Investigate seed 8042: instrument agent to capture route selection."""
import json, base64, gzip, zlib, copy, sys, os, statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent


def build_tracing_agent(variant, route_data):
    """Build agent that records route selection in a shared dict."""
    source = load_notebook_agent().replace('\r\n', '\n')
    
    # Apply the same modifications as build_agent_with_opening
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
    
    # Inject tracing: after _IMPL is created, hook into chassis._state to capture route
    hook = """
_ROUTE_TRACE = {}
_ORIG_STATE = _IMPL.chassis._state if hasattr(_IMPL, 'chassis') else None

def _trace_state(player, step):
    st = _ORIG_STATE(player, step)
    if player == 0 and 'route' in st:
        _ROUTE_TRACE['route'] = st['route']
    return st

if hasattr(_IMPL, 'chassis'):
    _IMPL.chassis._state = _trace_state
"""
    
    # Insert hook after the final agent function definition
    # Find the last line that defines agent
    lines = source.split('\n')
    insert_idx = len(lines) - 1
    # Find "def agent(" near the end
    for i in range(len(lines) - 1, max(0, len(lines) - 50), -1):
        if 'def agent(' in lines[i]:
            insert_idx = i
            break
    
    lines.insert(insert_idx, hook)
    source = '\n'.join(lines)
    
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def main():
    SEED = 8042
    route_data = load_route_data()
    
    print("=" * 70)
    print(f"INVESTIGATING SEED {SEED}: Route Selection & Opening Impact")
    print("=" * 70)
    
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant, route_data)
        trace = ns.get('_ROUTE_TRACE', {})
        
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        obs = copy.deepcopy(env.state[0].observation)
        action = agent_fn(obs)
        
        route = trace.get('route', None)
        print(f"\n[{variant.upper()}]")
        print(f"  Route selected: {route}")
        print(f"  Step 0 market: {action.get('market', [])}")
        
        # Get the route data
        impl = ns.get('_IMPL')
        if impl and hasattr(impl, 'chassis') and route is not None:
            chassis = impl.chassis
            if route in chassis.routes:
                tape = chassis.routes[route]
                
                # Count wheat across entire route
                wheat_buys = 0
                wheat_sells = 0
                for step_a in tape:
                    if not isinstance(step_a, dict):
                        continue
                    for o in (step_a.get('market') or []):
                        if not o or len(o) < 3:
                            continue
                        if o[1] == 'WHEAT':
                            if o[0] == 'BUY_PRODUCT':
                                wheat_buys += o[2]
                            elif o[0] == 'SELL':
                                wheat_sells += o[2]
                
                print(f"  Route wheat buys: {wheat_buys}")
                print(f"  Route wheat sells: {wheat_sells}")
                print(f"  Route wheat net: {wheat_buys - wheat_sells}")
                
                # Show shops
                for entry in route_data.get('shops', []):
                    if entry.get('route') == route:
                        print(f"  Route shops: {entry.get('shops', [])}")
                        break
                
                # Show first 5 steps of route
                print(f"  Route tape (steps 0-4):")
                for s in range(min(5, len(tape))):
                    a = tape[s]
                    if isinstance(a, dict):
                        print(f"    Step {s}: market={a.get('market', [])}")
                
                # Now run full game and track scores
                env2 = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
                env2.reset()
                env2.run([agent_fn, "starter"])
                score = env2.steps[-1][0].reward
                print(f"  Score vs starter: ${score:,.0f}")
    
    # Direct comparison
    print(f"\n{'='*70}")
    print(f"DIRECT COMPARISON (same seed {SEED})")
    print(f"{'='*70}")
    
    agents = {}
    for v in ['c9', 'original']:
        agents[v], _ = build_tracing_agent(v, route_data)
    
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
    env.reset()
    env.run([agents['c9'], agents['original']])
    r = [s.reward for s in env.steps[-1]]
    print(f"  H2H: C9=${r[0]:,.0f}  Original=${r[1]:,.0f}  diff=${r[0]-r[1]:+,.0f}")
    
    # Run each vs starter
    for v in ['c9', 'original']:
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agents[v], "starter"])
        score = env.steps[-1][0].reward
        print(f"  {v} vs starter: ${score:,.0f}")


if __name__ == "__main__":
    main()
