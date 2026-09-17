"""Phase 1: Opening extraction only (fast, no games)."""
import json, base64, gzip, zlib, copy, sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent

def main():
    route_data = load_route_data()
    bakery = {101,103,104,105,106,107,108,109,111,119,120}
    dynamic_bakery = set()
    for entry in route_data.get('shops', []):
        if 'BAKERY' in entry.get('shops', []):
            dynamic_bakery.add(entry.get('route'))
    print(f"BAKERY hardcoded: {sorted(bakery)}")
    print(f"BAKERY dynamic:   {sorted(dynamic_bakery)}")
    print(f"Match: {bakery == dynamic_bakery}")
    print(f"Total routes: {len(route_data.get('routes', {}))}")
    print()

    agents = {}
    for v in ['c9', 'original', 'minimal', 'none']:
        agents[v] = build_agent_with_opening(v, route_data)

    env = make("kaggriculture", configuration={"episodeSteps": 720})
    for v_name, agent_fn in agents.items():
        env.reset()
        obs = copy.deepcopy(env.state[0].observation)
        s0 = agent_fn(obs)
        env.step([s0, {"farmer": ["PASS"], "hands": [], "market": []}])
        obs = copy.deepcopy(env.state[0].observation)
        s1 = agent_fn(obs)
        m0 = s0.get('market', [])
        m1 = s1.get('market', [])
        print(f"[{v_name.upper()}]")
        print(f"  Step 0 ({len(m0)} orders): {m0}")
        print(f"  Step 1 ({len(m1)} orders): {m1}")
        print(f"  Farmer: {s0.get('farmer', [])}")
        print(f"  Hands:  {len(s0.get('hands', []))} workers")
        print()

    # Also check raw tape for a non-BAKERY route
    print("--- RAW TAPE (before any modification) ---")
    source = load_notebook_agent().replace('\r\n', '\n')
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
    ns = {'__builtins__': __builtins__}
    exec(compile(source.replace(old, ''), '<raw>', 'exec'), ns)
    raw_agent = ns['agent']
    env.reset()
    obs = copy.deepcopy(env.state[0].observation)
    s0 = raw_agent(obs)
    env.step([s0, {"farmer": ["PASS"], "hands": [], "market": []}])
    obs = copy.deepcopy(env.state[0].observation)
    s1 = raw_agent(obs)
    print(f"  Step 0 ({len(s0.get('market', []))} orders): {s0.get('market', [])}")
    print(f"  Step 1 ({len(s1.get('market', []))} orders): {s1.get('market', [])}")
    # Check route selected
    impl = ns.get('_IMPL')
    if impl and hasattr(impl, 'chassis'):
        st = impl.chassis.players.get(0, {})
        print(f"  Route: {st.get('route', 'unknown')}")

if __name__ == "__main__":
    main()
