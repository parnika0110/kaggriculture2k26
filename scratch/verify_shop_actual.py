"""Run C9 and Original on seed 7, compare actual town state at every step."""
import json, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make


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

# Run both variants
for variant in ['c9', 'original']:
    agent_fn = build_agent(variant)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED})
    env.reset()
    
    print(f"\n=== {variant.upper()} (seed {SEED}) ===")
    print(f"  env.info['seed'] = {env.info.get('seed', 'NOT SET')}")
    
    # Run through all steps, recording town at each day boundary
    prev_day = -1
    for step in range(720):
        obs = copy.deepcopy(env.state[0].observation)
        day = obs.get('day', 0)
        hour = obs.get('hour', 0)
        town = obs.get('town', {})
        shops = town.get('unlocked_shops', [])
        
        # Record at day boundaries
        if day != prev_day:
            print(f"  Step {step:>3} day={day} hour={hour}: shops={shops}")
            prev_day = day
        
        # Run one step
        action = agent_fn(obs)
        env.step([action, {"farmer": ["PASS"], "hands": [], "market": []}])
    
    # Final state
    obs = copy.deepcopy(env.state[0].observation)
    final_shops = obs.get('town', {}).get('unlocked_shops', [])
    score = obs.get('farms', [{}])[0].get('money', 0)
    print(f"  Final shops: {final_shops}")
    print(f"  Score: ${score:,.0f}")
