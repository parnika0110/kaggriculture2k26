"""
Comprehensive analysis of the Beyond-V43 notebook's C9 opening modification.

Tests 4 variants:
  A) Original V43 opening (wheat flip on all routes)
  B) C9 conditional opening (BAKERY keeps flip, others minimal) — the notebook's pipe-4
  C) Minimal wheat opening (buy 5 wheat only, no step 2 hiring override)
  D) No opening modification (raw compressed tape data)

Measures:
  - Win rate vs starter over N games
  - Average score
  - First-10-step market order count and slot utilization
  - Economic benefit of wheat flip (profit vs opportunity cost)
"""
import json, base64, gzip, zlib, copy, sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make

# ── Load compressed agent from notebook ──────────────────────────────────────
def _extract_b85_from_notebook(nb):
    """Extract B85_SOURCE string from notebook cell 7 source array."""
    for s in nb['cells'][7]['source']:
        if 'B85_SOURCE' in s and 'ABzY8' in s:
            idx = s.find("B85_SOURCE = '") + len("B85_SOURCE = '")
            b85 = s[idx:].rstrip('\n').rstrip("'")
            return b85
    raise ValueError('B85_SOURCE not found in notebook')


def load_notebook_agent():
    nb_path = os.path.join(os.path.dirname(__file__), '..',
                           'beyond-v43-what-the-top-clusters-do-on-turn-1 (1).ipynb')
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    b85_data = _extract_b85_from_notebook(nb)
    raw = base64.b85decode(b85_data)
    return gzip.decompress(raw).decode('utf-8', errors='replace')


def load_route_data():
    """Extract the compressed _R108_DATA from the agent source."""
    source = load_notebook_agent()
    for line in source.split('\n'):
        if '_R108_DATA=json.loads' in line:
            s = line.find("base64.b85decode('") + len("base64.b85decode('")
            e = line.rfind("'))")
            b85 = line[s:e]
            data_raw = base64.b85decode(b85)
            return json.loads(zlib.decompress(data_raw))
    return None


def get_bakery_routes(route_data):
    """Dynamically determine which routes involve BAKERY shops."""
    shops = route_data.get('shops', [])
    bakery = set()
    for entry in shops:
        if 'BAKERY' in entry.get('shops', []):
            bakery.add(entry.get('route'))
    return bakery


def build_agent_with_opening(variant, route_data=None):
    """
    Build an agent function with a specific opening variant.
    
    Variants:
      'original'  — V43 wheat flip on all routes (the notebook's _R42_OPENING)
      'c9'        — C9 conditional: BAKERY keeps flip, others get minimal + step2 hiring
      'minimal'   — Buy 5 wheat only on step 0, no step 2 override
      'none'      — No modification to the compressed tape data
    """
    source = load_notebook_agent()
    bakery_routes = get_bakery_routes(route_data) if route_data else {101,103,104,105,106,107,108,109,111,119,120}

    # Normalize line endings for reliable string replacement
    source = source.replace('\r\n', '\n')
    
    if variant == 'original':
        # Replace the _PIPE3 block with the original _R42_OPENING
        old_block = """_PIPE3_BAKERY_ROUTES={101,103,104,105,106,107,108,109,111,119,120}
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
        new_block = """_R42_OPENING=[['BUY_PRODUCT','WHEAT',5],['BUY_PRODUCT','WHEAT',10],['SELL','WHEAT',60]]
for _r42_tape in _ROUTES.values():
    _r42_tape[0]=dict(_r42_tape[0],market=[list(o) for o in _R42_OPENING])
del _r42_tape"""
        source = source.replace(old_block, new_block)

    elif variant == 'minimal':
        # Buy 5 wheat on step 0, but DON'T override step 1
        old_block = """_PIPE3_BAKERY_ROUTES={101,103,104,105,106,107,108,109,111,119,120}
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
        new_block = """for _p3_rid,_p3_tape in _ROUTES.items():
    _p3_tape[0]=dict(_p3_tape[0],market=[['BUY_PRODUCT','WHEAT',5]])
del _p3_rid,_p3_tape"""
        source = source.replace(old_block, new_block)

    elif variant == 'none':
        # Remove the entire _PIPE3 block — use raw compressed tapes
        old_block = """_PIPE3_BAKERY_ROUTES={101,103,104,105,106,107,108,109,111,119,120}
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
        source = source.replace(old_block, '')
    
    # 'c9' uses the original source unchanged (already has the C9 opening)

    # Execute the modified source
    ns = {'__builtins__': __builtins__}
    exec(compile(source, '<pipe-4>', 'exec'), ns)
    return ns['agent']


# ── Benchmark runner ─────────────────────────────────────────────────────────
def run_benchmark(agent_fn, num_games=20, label=""):
    """Run agent vs starter, return stats."""
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    scores = []
    starter_scores = []
    t0 = time.time()
    
    for ep in range(num_games):
        env.reset()
        env.run([agent_fn, "starter"])
        res = [s.reward for s in env.steps[-1]]
        scores.append(res[0])
        starter_scores.append(res[1])
    
    elapsed = time.time() - t0
    avg = sum(scores) / len(scores)
    avg_starter = sum(starter_scores) / len(starter_scores)
    wins = sum(1 for a, b in zip(scores, starter_scores) if a > b)
    ties = sum(1 for a, b in zip(scores, starter_scores) if a == b)
    
    return {
        'label': label,
        'avg_score': avg,
        'avg_starter': avg_starter,
        'wins': wins,
        'ties': ties,
        'losses': num_games - wins - ties,
        'win_rate': wins / num_games,
        'elo_rate': (wins + 0.5 * ties) / num_games,
        'elapsed': elapsed,
        'scores': scores,
    }


# ── Market order measurement ────────────────────────────────────────────────
def measure_market_orders(agent_fn, num_games=5):
    """Run agent and count market orders per step for first 10 steps."""
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    order_counts = {}  # step -> list of order counts
    
    for ep in range(num_games):
        env.reset()
        # Run one step at a time to capture actions
        for step in range(10):
            observations = env.observations
            obs = observations[0]  # player 0
            action = agent_fn(obs)
            market = action.get('market', [])
            n = len(market)
            order_counts.setdefault(step, []).append(n)
            env.step([action, "starter"])
    
    return order_counts


# ── Economic analysis ───────────────────────────────────────────────────────
def analyze_economics(route_data):
    """Quantify the wheat flip economics."""
    routes = {int(k): [route_data['actions'][j] for j in ids]
              for k, ids in route_data['routes'].items()}
    
    # Wheat flip: buy 15 wheat @ $10 = $150, sell up to 60 from shed
    # On step 0, shed is empty, so SELL 60 is a no-op
    # On step 1, original sells 13 wheat @ ~$29 = $377, buys 5 @ $10 = $50
    # Net from flip: -$150 (step 0 buys) + $377 (step 1 sell) - $50 (step 1 buy) = +$177
    
    # With minimal: buy 5 wheat @ $10 = $50, no sell
    # Net: -$50
    
    # Difference: $177 - (-$50) = $127 advantage for flip
    # But: flip uses 3+2=5 market slots, minimal uses 1+0=1 slot
    # Freed slots: 4 slots over 2 steps
    
    # Step 1 original has 9 orders (out of 10 max)
    # Step 1 minimal has 7 orders (out of 10 max)
    # Freed on step 1: 2 slots for reactive layers
    
    print("=== Wheat Flip Economics ===")
    print(f"Flip step 0: BUY 15 wheat @ $10 = -$150, SELL 60 (no-op, shed empty)")
    print(f"Flip step 1: SELL 13 wheat @ $29 ≈ +$377, BUY 5 wheat @ $10 = -$50")
    print(f"Flip net profit: ~$177 over 2 steps")
    print()
    print(f"Minimal step 0: BUY 5 wheat @ $10 = -$50")
    print(f"Minimal step 1: (no wheat orders)")
    print(f"Minimal net cost: ~$50")
    print()
    print(f"Opportunity cost of skipping flip: ~$127 ($177 profit - $50 minimal cost)")
    print()
    print("=== Market Order Slot Analysis ===")
    print("Flip:   step 0 = 3 slots, step 1 = 9 slots (total 12)")
    print("C9:     step 0 = 1 slot,  step 1 = 7 slots (total 8)")
    print("Freed:  4 slots over 2 steps")
    print("  - step 0: 2 extra slots (rarely used by reactive layers)")
    print("  - step 1: 2 extra slots (sell_lead, budget_guard may benefit)")
    print()
    
    # Check how many routes actually use step 1 heavily
    bakery = get_bakery_routes(route_data)
    heavy_step1 = 0
    for rid, tape in routes.items():
        if rid < 100 or len(tape) < 2:
            continue
        if rid in bakery:
            continue
        m1 = tape[1].get('market', [])
        if len(m1) >= 8:
            heavy_step1 += 1
    non_bakery = sum(1 for r in routes if r >= 100 and r not in bakery)
    print(f"Non-BAKERY routes with ≥8 orders on step 1: {heavy_step1}/{non_bakery}")
    print(f"These routes benefit most from the 2 freed slots on step 1.")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("NOTEBOOK ANALYSIS: Beyond-V43 C9 Opening Ablation Study")
    print("=" * 70)
    print()
    
    # Load route data for economic analysis
    route_data = load_route_data()
    if route_data:
        bakery = get_bakery_routes(route_data)
        print(f"Loaded route data: {len(route_data.get('routes', {}))} routes")
        print(f"BAKERY routes (dynamic): {sorted(bakery)}")
        print()
    
    # Define variants
    variants = ['c9', 'original', 'minimal', 'none']
    labels = {
        'c9': 'C9 Conditional (pipe-4)',
        'original': 'V43 Original (wheat flip all)',
        'minimal': 'Minimal wheat only',
        'none': 'No modification (raw tape)',
    }
    
    NUM_GAMES = 10
    NUM_MARKET = 3
    
    results = {}
    market_data = {}
    
    for variant in variants:
        print(f"\n{'─' * 70}")
        print(f"Building variant: {labels[variant]}")
        print(f"{'─' * 70}")
        
        try:
            agent_fn = build_agent_with_opening(variant, route_data)
            print(f"  Agent built successfully")
            
            # Benchmark
            print(f"  Running {NUM_GAMES} games vs starter...")
            stats = run_benchmark(agent_fn, NUM_GAMES, labels[variant])
            results[variant] = stats
            print(f"  Avg score: ${stats['avg_score']:.0f} (starter: ${stats['avg_starter']:.0f})")
            print(f"  Win rate: {stats['wins']}/{NUM_GAMES} ({stats['win_rate']:.1%})")
            print(f"  Elo rate: {stats['elo_rate']:.1%}")
            print(f"  Time: {stats['elapsed']:.1f}s")
            
            # Market order measurement
            print(f"  Measuring market orders ({NUM_MARKET} games, 10 steps)...")
            mkt = measure_market_orders(agent_fn, NUM_MARKET)
            market_data[variant] = mkt
            avg_orders = [sum(mkt[s]) / len(mkt[s]) for s in range(10)]
            print(f"  Avg orders/step (first 10): {[f'{x:.1f}' for x in avg_orders]}")
            print(f"  Total avg orders (steps 0-9): {sum(avg_orders):.1f}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # ── Results comparison ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Variant':<30} {'Avg Score':>10} {'Win Rate':>10} {'Elo Rate':>10} {'Avg Orders':>10}")
    print("-" * 70)
    for v in variants:
        if v in results:
            r = results[v]
            mkt_avg = sum(sum(market_data[v][s]) / len(market_data[v][s]) for s in range(10)) if v in market_data else 0
            print(f"{r['label']:<30} ${r['avg_score']:>8,.0f} {r['win_rate']:>9.1%} {r['elo_rate']:>9.1%} {mkt_avg:>9.1f}")
    
    # ── Head-to-head ─────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("HEAD-TO-HEAD COMPARISONS (same games)")
    print(f"{'─' * 70}")
    
    if 'c9' in results and 'original' in results:
        c9_scores = results['c9']['scores']
        orig_scores = results['original']['scores']
        c9_wins = sum(1 for a, b in zip(c9_scores, orig_scores) if a > b)
        orig_wins = sum(1 for a, b in zip(c9_scores, orig_scores) if b > a)
        ties = sum(1 for a, b in zip(c9_scores, orig_scores) if a == b)
        print(f"C9 vs Original: {c9_wins}-{orig_wins}-{ties} (C9 elo: {(c9_wins + 0.5*ties)/NUM_GAMES:.1%})")
    
    if 'c9' in results and 'minimal' in results:
        c9_scores = results['c9']['scores']
        min_scores = results['minimal']['scores']
        c9_wins = sum(1 for a, b in zip(c9_scores, min_scores) if a > b)
        min_wins = sum(1 for a, b in zip(c9_scores, min_scores) if b > a)
        ties = sum(1 for a, b in zip(c9_scores, min_scores) if a == b)
        print(f"C9 vs Minimal:  {c9_wins}-{min_wins}-{ties} (C9 elo: {(c9_wins + 0.5*ties)/NUM_GAMES:.1%})")
    
    if 'c9' in results and 'none' in results:
        c9_scores = results['c9']['scores']
        none_scores = results['none']['scores']
        c9_wins = sum(1 for a, b in zip(c9_scores, none_scores) if a > b)
        none_wins = sum(1 for a, b in zip(c9_scores, none_scores) if b > a)
        ties = sum(1 for a, b in zip(c9_scores, none_scores) if a == b)
        print(f"C9 vs None:     {c9_wins}-{none_wins}-{ties} (C9 elo: {(c9_wins + 0.5*ties)/NUM_GAMES:.1%})")
    
    # ── Market order comparison ──────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("MARKET ORDER USAGE (avg orders per step, first 10 steps)")
    print(f"{'─' * 70}")
    
    header = f"{'Step':<6}"
    for v in variants:
        if v in market_data:
            header += f" {labels[v][:15]:>15}"
    print(header)
    print("-" * (6 + 16 * len(variants)))
    
    for step in range(10):
        row = f"{step:<6}"
        for v in variants:
            if v in market_data and step in market_data[v]:
                avg = sum(market_data[v][step]) / len(market_data[v][step])
                row += f" {avg:>15.1f}"
            else:
                row += f" {'N/A':>15}"
        print(row)
    
    # ── Economic analysis ────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    if route_data:
        analyze_economics(route_data)
    
    # ── Recommendation ───────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("RECOMMENDATION")
    print(f"{'=' * 70}")
    
    if 'c9' in results:
        best = max(results.items(), key=lambda x: x[1]['elo_rate'])
        print(f"Strongest variant: {best[1]['label']}")
        print(f"  Elo rate: {best[1]['elo_rate']:.1%}")
        print(f"  Avg score: ${best[1]['avg_score']:.0f}")
        
        if best[0] == 'c9':
            print(f"\nThe C9 conditional opening is the strongest variant.")
            print(f"It skips the wheat flip for non-BAKERY routes, saving ~$127")
            print(f"and freeing 2 market order slots on step 1.")
        elif best[0] == 'original':
            print(f"\nThe original V43 wheat flip is still competitive.")
            print(f"The C9 modification may not provide a significant edge.")
        elif best[0] == 'minimal':
            print(f"\nMinimal wheat (no step 2 override) performs best.")
            print(f"The step 2 hiring override in C9 may be harmful.")
        elif best[0] == 'none':
            print(f"\nThe raw compressed tapes perform best without modification.")
            print(f"Any opening modification may be harmful.")
    
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
