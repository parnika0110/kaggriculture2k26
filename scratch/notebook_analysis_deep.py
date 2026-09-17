"""Phase 4: Deep dive - opening comparison + focused H2H (faster)."""
import json, base64, gzip, zlib, copy, sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent


def show_openings():
    """Show what each variant does on step 0 and 1."""
    print("=" * 70)
    print("OPENING COMPARISON")
    print("=" * 70)
    
    route_data = load_route_data()
    variants = {}
    for v in ['c9', 'original', 'minimal', 'none']:
        variants[v] = build_agent_with_opening(v, route_data)
    
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    
    for v_name, agent_fn in variants.items():
        env.reset()
        obs = copy.deepcopy(env.state[0].observation)
        s0 = agent_fn(obs)
        env.step([s0, {"farmer": ["PASS"], "hands": [], "market": []}])
        obs = copy.deepcopy(env.state[0].observation)
        s1 = agent_fn(obs)
        m0 = s0.get('market', [])
        m1 = s1.get('market', [])
        print(f"\n{v_name.upper():>10}:")
        print(f"  Step 0 ({len(m0)} orders): {m0}")
        print(f"  Step 1 ({len(m1)} orders): {m1}")
    
    # Show raw tape
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
    print(f"\n{'RAW':>10}:")
    print(f"  Step 0 ({len(s0.get('market', []))} orders): {s0.get('market', [])}")
    print(f"  Step 1 ({len(s1.get('market', []))} orders): {s1.get('market', [])}")
    
    # Check which route was selected
    impl = ns.get('_IMPL', None)
    if impl and hasattr(impl, 'chassis'):
        st = impl.chassis.players.get(0, {})
        route = st.get('route', 'unknown')
        print(f"\n  Selected route: {route}")


def run_focused_h2h():
    """Focused H2H with 10 games."""
    route_data = load_route_data()
    agents = {}
    for v in ['c9', 'original', 'none', 'minimal']:
        agents[v] = build_agent_with_opening(v, route_data)
    
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    NUM = 10
    
    matchups = [
        ('c9', 'original', 'C9 vs Original'),
        ('original', 'c9', 'Original vs C9'),
        ('c9', 'none', 'C9 vs Raw Tape'),
        ('none', 'c9', 'Raw Tape vs C9'),
        ('original', 'none', 'Original vs Raw Tape'),
        ('none', 'original', 'Raw Tape vs Original'),
    ]
    
    print(f"\n{'='*70}")
    print(f"FOCUSED H2H ({NUM} games each)")
    print(f"{'='*70}")
    print(f"{'Matchup':<25} {'A avg':>10} {'B avg':>10} {'A wins':>8} {'B wins':>8}")
    print("-" * 65)
    
    for a_key, b_key, label in matchups:
        a_wins = b_wins = ties = 0
        a_scores = []
        b_scores = []
        for ep in range(NUM):
            env.reset()
            env.run([agents[a_key], agents[b_key]])
            res = [s.reward for s in env.steps[-1]]
            a_scores.append(res[0])
            b_scores.append(res[1])
            if res[0] > res[1]: a_wins += 1
            elif res[1] > res[0]: b_wins += 1
            else: ties += 1
        a_avg = sum(a_scores) / len(a_scores)
        b_avg = sum(b_scores) / len(b_scores)
        print(f"{label:<25} ${a_avg:>9,.0f} ${b_avg:>9,.0f} {a_wins:>8} {b_wins:>8}")


if __name__ == "__main__":
    show_openings()
    run_focused_h2h()
