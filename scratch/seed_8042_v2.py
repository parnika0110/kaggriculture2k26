"""Investigate seed 8042: capture route by patching act(), trace economics."""
import json, base64, gzip, zlib, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent

SEED = 8042
route_data = load_route_data()

def build_tracing_agent(variant):
    """Build agent with route-tracing hook."""
    source = load_notebook_agent().replace('\r\n', '\n')
    
    # Apply variant modifications
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
    
    # Inject route capture hook at the end
    hook = """
_ROUTE_LOG = []

_orig_act = _IMPL.chassis.act
def _traced_act(observation, configuration=None):
    import copy as _cp
    step_val = observation.get('step', 0) if isinstance(observation, dict) else 0
    player_val = observation.get('player', 0) if isinstance(observation, dict) else 0
    result = _orig_act(observation, configuration)
    if player_val == 0:
        st = _IMPL.chassis.players.get(0, {})
        route = st.get('route', None)
        market = result.get('market', []) if isinstance(result, dict) else []
        _ROUTE_LOG.append({'step': step_val, 'route': route, 'market': market})
    return result
_IMPL.chassis.act = _traced_act
"""
    source = source.rstrip() + '\n' + hook + '\n'
    
    ns = {'__builtins__': __builtins__}
    exec(compile(source, f'<{variant}>', 'exec'), ns)
    return ns['agent'], ns


def main():
    print("=" * 70)
    print(f"SEED {SEED} DEEP INVESTIGATION")
    print("=" * 70)
    
    # ── Part 1: Compare vs starter ──
    print("\n--- Part 1: Score comparison (vs starter) ---")
    for variant in ['c9', 'original']:
        agent_fn, ns = build_tracing_agent(variant)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
        env.reset()
        env.run([agent_fn, "starter"])
        score = env.steps[-1][0].reward
        log = ns.get('_ROUTE_LOG', [])
        
        # Find route from log
        routes_seen = set(e['route'] for e in log if e['route'] is not None)
        print(f"  {variant:>10}: ${score:>10,.0f}  routes: {routes_seen}")
        
        # Show first 5 steps
        print(f"    First 5 steps:")
        for e in log[:5]:
            print(f"      step={e['step']:>2}  route={e['route']}  market={e['market']}")
    
    # ── Part 2: Route analysis ──
    print("\n--- Part 2: Route details ---")
    # Run original agent and capture all routes
    agent_orig, ns_orig = build_tracing_agent('original')
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
    env.reset()
    env.run([agent_orig, "starter"])
    log_orig = ns_orig.get('_ROUTE_LOG', [])
    routes_orig = [e['route'] for e in log_orig if e['route'] is not None]
    
    if routes_orig:
        primary_route = routes_orig[0]
        print(f"  Original primary route: {primary_route}")
        
        # Get route data from the agent's internal routes
        # We need to access the routes from the agent's module
        source = load_notebook_agent().replace('\r\n', '\n')
        ns_routes = {'__builtins__': __builtins__}
        exec(compile(source, '<routes>', 'exec'), ns_routes)
        impl = ns_routes['_IMPL']
        chassis = impl.chassis
        
        if primary_route and primary_route in chassis.routes:
            tape = chassis.routes[primary_route]
            
            # Wheat analysis
            wheat_buys = 0
            wheat_sells = 0
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
            
            print(f"    Wheat buys: {wheat_buys}")
            print(f"    Wheat sells: {wheat_sells}")
            print(f"    Wheat net: {wheat_buys - wheat_sells}")
            
            # Show all steps with market orders
            print(f"    All market orders:")
            for s in range(len(tape)):
                a = tape[s]
                if isinstance(a, dict) and a.get('market'):
                    sells = [o for o in a['market'] if o and o[0] == 'SELL']
                    buys = [o for o in a['market'] if o and o[0] != 'SELL']
                    if sells or buys:
                        print(f"      Step {s:>3}: SELL={sells}  BUY/HIRE={len(buys)} orders")
            
            # Shops
            for entry in route_data.get('shops', []):
                if entry.get('route') == primary_route:
                    print(f"    Shops: {entry.get('shops', [])}")
                    break
        else:
            print(f"    Route {primary_route} not in chassis.routes")
            print(f"    Available routes: {sorted(chassis.routes.keys())[:10]}...")
    
    # ── Part 3: C9 route ──
    agent_c9, ns_c9 = build_tracing_agent('c9')
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
    env.reset()
    env.run([agent_c9, "starter"])
    log_c9 = ns_c9.get('_ROUTE_LOG', [])
    routes_c9 = [e['route'] for e in log_c9 if e['route'] is not None]
    print(f"\n  C9 primary route: {routes_c9[0] if routes_c9 else None}")
    
    # ── Part 4: Are they the same route? ──
    if routes_orig and routes_c9:
        same = routes_orig[0] == routes_c9[0]
        print(f"\n  Same route? {same}")
        if not same:
            print(f"  CRITICAL: Different routes selected!")
            print(f"    Original: {routes_orig[0]}")
            print(f"    C9: {routes_c9[0]}")


if __name__ == "__main__":
    main()
