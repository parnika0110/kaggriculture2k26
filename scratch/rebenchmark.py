"""Re-run 30-seed benchmark with saved agent to verify failure rate."""
import json, sys, os, statistics, time
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from kaggle_environments import make

SEEDS = list(range(30))

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

print("Building agents...")
agents = {'c9': build_agent('c9'), 'original': build_agent('original')}
print("Done.\n")

results = []
t0 = time.time()
for i, seed in enumerate(SEEDS):
    scores = {}
    for variant, agent_fn in agents.items():
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
        env.reset()
        env.run([agent_fn, "starter"])
        scores[variant] = env.steps[-1][0].reward
    diff = scores['c9'] - scores['original']
    winner = "C9" if diff > 0 else "Original" if diff < 0 else "Tie"
    results.append({'seed': seed, 'c9': scores['c9'], 'original': scores['original'], 'diff': diff, 'winner': winner})
    if (i+1) % 10 == 0:
        elapsed = time.time() - t0
        c9_w = sum(1 for r in results if r['winner'] == 'C9')
        orig_w = sum(1 for r in results if r['winner'] == 'Original')
        print(f"  [{i+1}/{len(SEEDS)}] C9: {c9_w}  Orig: {orig_w}  ({elapsed:.0f}s)")

# Results
c9_wins = [r for r in results if r['winner'] == 'C9']
orig_wins = [r for r in results if r['winner'] == 'Original']
diffs = [r['diff'] for r in results]

print(f"\n--- Win rates ---")
print(f"C9 wins: {len(c9_wins)}/{len(SEEDS)} ({len(c9_wins)/len(SEEDS):.1%})")
print(f"Original wins: {len(orig_wins)}/{len(SEEDS)} ({len(orig_wins)/len(SEEDS):.1%})")

print(f"\n--- Score statistics ---")
c9_scores = [r['c9'] for r in results]
orig_scores = [r['original'] for r in results]
print(f"Mean diff: ${statistics.mean(diffs):+,.0f}")
print(f"Median diff: ${statistics.median(diffs):+,.0f}")
print(f"Stdev diff: ${statistics.stdev(diffs):+,.0f}")

if orig_wins:
    fail_diffs = [-r['diff'] for r in orig_wins]
    print(f"\n--- Failure analysis ---")
    print(f"Failure rate: {len(orig_wins)}/{len(SEEDS)} ({len(orig_wins)/len(SEEDS):.1%})")
    print(f"Avg failure size: ${statistics.mean(fail_diffs):+,.0f}")
    print(f"Failure seeds: {[r['seed'] for r in orig_wins]}")

# Per-seed detail
print(f"\n--- Per-seed results ---")
print(f"{'Seed':>6} {'C9':>10} {'Orig':>10} {'Diff':>10} {'Winner':>10}")
print("-" * 50)
for r in results:
    print(f"{r['seed']:>6} ${r['c9']:>9,.0f} ${r['original']:>9,.0f} ${r['diff']:>+9,.0f} {r['winner']:>10}")

# Save
with open('scratch/rebenchmark_results.json', 'w') as f:
    json.dump(results, f, indent=2)
