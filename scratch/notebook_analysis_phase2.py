"""
Phase 2: Direct H2H test matching notebook methodology, plus market order measurement.
Tests C9 vs Original in direct head-to-head (same game, both agents play).
"""
import json, base64, gzip, zlib, copy, sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make

# Reuse loader from phase 1
from notebook_analysis import load_notebook_agent, build_agent_with_opening, load_route_data, get_bakery_routes


def run_h2h(agent_a, agent_b, num_games=20, label_a="A", label_b="B"):
    """Direct head-to-head: both agents play the same game."""
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    a_wins = b_wins = ties = 0
    a_scores = []
    b_scores = []
    
    for ep in range(num_games):
        env.reset()
        env.run([agent_a, agent_b])
        res = [s.reward for s in env.steps[-1]]
        a_scores.append(res[0])
        b_scores.append(res[1])
        if res[0] > res[1]:
            a_wins += 1
        elif res[1] > res[0]:
            b_wins += 1
        else:
            ties += 1
    
    a_elo = (a_wins + 0.5 * ties) / num_games
    return {
        'a_wins': a_wins, 'b_wins': b_wins, 'ties': ties,
        'a_elo': a_elo, 'b_elo': 1 - a_elo,
        'a_avg': sum(a_scores) / len(a_scores),
        'b_avg': sum(b_scores) / len(b_scores),
        'a_scores': a_scores, 'b_scores': b_scores,
    }


def measure_market_orders_sequential(agent_fn, num_games=3):
    """Measure market orders by running agent step-by-step."""
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    order_counts = {}
    
    for ep in range(num_games):
        env.reset()
        for step in range(10):
            # Get the observation for player 0
            obs = copy.deepcopy(env.state[0].observation) if hasattr(env, 'state') else None
            if obs is None:
                # Fallback: use env.observation if available
                try:
                    obs = env.observation
                except:
                    break
            
            action = agent_fn(obs)
            market = action.get('market', [])
            n = len(market)
            order_counts.setdefault(step, []).append(n)
            
            # Step both players
            obs1 = copy.deepcopy(env.state[1].observation) if hasattr(env, 'state') and len(env.state) > 1 else None
            starter_action = {"farmer": ["PASS"], "hands": [], "market": []}
            env.step([action, starter_action])
    
    return order_counts


def measure_market_via_replay(agent_fn, num_games=3):
    """Measure market orders by inspecting the agent's output directly."""
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    order_counts = {}
    
    for ep in range(num_games):
        env.reset()
        # Run one full game, capturing actions at each step
        for step in range(10):
            # Get observations
            observations = env.observation
            obs = observations[0]
            action = agent_fn(obs)
            market = action.get('market', [])
            order_counts.setdefault(step, []).append(len(market))
            env.step([action, {"farmer": ["PASS"], "hands": [], "market": []}])
    
    return order_counts


def main():
    print("=" * 70)
    print("PHASE 2: Direct H2H + Market Order Analysis")
    print("=" * 70)
    
    route_data = load_route_data()
    
    # Build agents
    print("\nBuilding agents...")
    c9_agent = build_agent_with_opening('c9', route_data)
    orig_agent = build_agent_with_opening('original', route_data)
    none_agent = build_agent_with_opening('none', route_data)
    minimal_agent = build_agent_with_opening('minimal', route_data)
    print("All agents built successfully")
    
    # Direct H2H: C9 vs Original (matches notebook methodology)
    print("\n--- Direct H2H: C9 vs Original (20 games) ---")
    r = run_h2h(c9_agent, orig_agent, 20, "C9", "Original")
    print(f"  C9 wins:     {r['a_wins']}/20")
    print(f"  Original wins: {r['b_wins']}/20")
    print(f"  Ties:        {r['ties']}/20")
    print(f"  C9 elo rate: {r['a_elo']:.1%}")
    print(f"  C9 avg score: ${r['a_avg']:,.0f}")
    print(f"  Original avg: ${r['b_avg']:,.0f}")
    
    # Direct H2H: C9 vs None (raw tapes)
    print("\n--- Direct H2H: C9 vs None/raw (20 games) ---")
    r2 = run_h2h(c9_agent, none_agent, 20, "C9", "None")
    print(f"  C9 wins:     {r2['a_wins']}/20")
    print(f"  None wins:   {r2['b_wins']}/20")
    print(f"  Ties:        {r2['ties']}/20")
    print(f"  C9 elo rate: {r2['a_elo']:.1%}")
    print(f"  C9 avg score: ${r2['a_avg']:,.0f}")
    print(f"  None avg:    ${r2['b_avg']:,.0f}")
    
    # Direct H2H: Original vs None
    print("\n--- Direct H2H: Original vs None/raw (20 games) ---")
    r3 = run_h2h(orig_agent, none_agent, 20, "Original", "None")
    print(f"  Original wins: {r3['a_wins']}/20")
    print(f"  None wins:   {r3['b_wins']}/20")
    print(f"  Ties:        {r3['ties']}/20")
    print(f"  Original elo: {r3['a_elo']:.1%}")
    
    # Direct H2H: Minimal vs None
    print("\n--- Direct H2H: Minimal vs None/raw (20 games) ---")
    r4 = run_h2h(minimal_agent, none_agent, 20, "Minimal", "None")
    print(f"  Minimal wins: {r4['a_wins']}/20")
    print(f"  None wins:   {r4['b_wins']}/20")
    print(f"  Ties:        {r4['ties']}/20")
    print(f"  Minimal elo: {r4['a_elo']:.1%}")
    
    # Market order measurement
    print("\n--- Market Order Usage (first 10 steps) ---")
    try:
        mkt_c9 = measure_market_via_replay(c9_agent, 3)
        mkt_orig = measure_market_via_replay(orig_agent, 3)
        
        print(f"{'Step':<6} {'C9':>8} {'Original':>10} {'Delta':>8}")
        print("-" * 35)
        for step in range(10):
            c9_avg = sum(mkt_c9.get(step, [0])) / max(len(mkt_c9.get(step, [1])), 1)
            orig_avg = sum(mkt_orig.get(step, [0])) / max(len(mkt_orig.get(step, [1])), 1)
            delta = c9_avg - orig_avg
            print(f"{step:<6} {c9_avg:>8.1f} {orig_avg:>10.1f} {delta:>+8.1f}")
        
        c9_total = sum(sum(mkt_c9.get(s, [0])) / max(len(mkt_c9.get(s, [1])), 1) for s in range(10))
        orig_total = sum(sum(mkt_orig.get(s, [0])) / max(len(mkt_orig.get(s, [1])), 1) for s in range(10))
        print(f"\nTotal orders (steps 0-9): C9={c9_total:.0f}, Original={orig_total:.0f}")
    except Exception as e:
        print(f"  Market measurement failed: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nDirect H2H results (20 games each):")
    print(f"  C9 vs Original:    C9 elo = {r['a_elo']:.1%}  (C9 avg ${r['a_avg']:,.0f} vs ${r['b_avg']:,.0f})")
    print(f"  C9 vs None/raw:    C9 elo = {r2['a_elo']:.1%}  (C9 avg ${r2['a_avg']:,.0f} vs ${r2['b_avg']:,.0f})")
    print(f"  Original vs None:  Orig elo = {r3['a_elo']:.1%}")
    print(f"  Minimal vs None:   Min elo = {r4['a_elo']:.1%}")
    
    # Determine winner
    elo_results = {
        'C9': r['a_elo'],
        'Original': r3['a_elo'],  # vs None
        'Minimal': r4['a_elo'],   # vs None
        'None': 0.5,              # baseline
    }
    best = max(elo_results, key=elo_results.get)
    print(f"\nStrongest variant: {best} (elo vs None/raw: {elo_results[best]:.1%})")
    
    if best == 'Original':
        print("The wheat flip is still competitive. C9 modification does NOT improve over V43.")
    elif best == 'C9':
        print("The C9 conditional opening provides a measurable edge over raw V43.")
    elif best == 'None':
        print("The raw compressed tapes perform best without any opening modification.")
    elif best == 'Minimal':
        print("Minimal wheat (no step 2 override) performs best.")


if __name__ == "__main__":
    main()
