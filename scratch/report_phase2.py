"""Phase 2: Benchmark vs starter + bidirectional H2H."""
import json, copy, sys, os, time, statistics
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
from notebook_analysis import build_agent_with_opening, load_route_data

def main():
    route_data = load_route_data()
    agents = {}
    for v in ['c9', 'original', 'minimal', 'none']:
        agents[v] = build_agent_with_opening(v, route_data)

    NUM = 8
    env = make("kaggriculture", configuration={"episodeSteps": 720})

    # ── Benchmark vs starter ──
    print(f"=== BENCHMARK vs STARTER ({NUM} games each) ===")
    print(f"{'Variant':<12} {'Mean':>10} {'Median':>10} {'Stdev':>10} {'Min':>10} {'Max':>10}")
    print("-" * 68)
    bench_scores = {}
    for v in ['c9', 'original', 'minimal', 'none']:
        scores = []
        t0 = time.time()
        for _ in range(NUM):
            env.reset()
            env.run([agents[v], "starter"])
            scores.append(env.steps[-1][0].reward)
        elapsed = time.time() - t0
        bench_scores[v] = scores
        mean = statistics.mean(scores)
        med = statistics.median(scores)
        sd = statistics.stdev(scores) if len(scores) > 1 else 0
        print(f"{v:<12} ${mean:>9,.0f} ${med:>9,.0f} ${sd:>9,.0f} ${min(scores):>9,.0f} ${max(scores):>9,.0f}  ({elapsed:.0f}s)")
    print()

    # ── Bidirectional H2H ──
    keys = ['c9', 'original', 'minimal', 'none']
    pairs = []
    for i in range(len(keys)):
        for j in range(i+1, len(keys)):
            pairs.append((keys[i], keys[j]))

    print(f"=== BIDIRECTIONAL H2H ({NUM} games each direction) ===")
    h2h = {}
    for a, b in pairs:
        a_scores, b_scores = [], []
        a_wins = b_wins = ties = 0
        for _ in range(NUM):
            env.reset()
            env.run([agents[a], agents[b]])
            r = [s.reward for s in env.steps[-1]]
            a_scores.append(r[0])
            b_scores.append(r[1])
            if r[0] > r[1]: a_wins += 1
            elif r[1] > r[0]: b_wins += 1
            else: ties += 1
        elo_a = (a_wins + 0.5*ties) / NUM
        elo_b = (b_wins + 0.5*ties) / NUM
        h2h[(a,b)] = {'a_wins': a_wins, 'b_wins': b_wins, 'ties': ties,
                       'elo_a': elo_a, 'elo_b': elo_b,
                       'a_mean': statistics.mean(a_scores), 'b_mean': statistics.mean(b_scores),
                       'a_scores': a_scores, 'b_scores': b_scores}

    print(f"\n{'Matchup':<28} {'A wins':>6} {'B wins':>6} {'Ties':>5} {'Elo A':>7} {'Elo B':>7} {'A mean$':>10} {'B mean$':>10}")
    print("-" * 82)
    for (a, b), h in sorted(h2h.items()):
        print(f"{a+' vs '+b:<28} {h['a_wins']:>6} {h['b_wins']:>6} {h['ties']:>5} {h['elo_a']:>6.1%} {h['elo_b']:>6.1%} ${h['a_mean']:>9,.0f} ${h['b_mean']:>9,.0f}")

    # ── Win-rate matrix ──
    print(f"\n=== WIN-RATE MATRIX (row elo against column) ===")
    print(f"{'':>12}", end="")
    for v in keys:
        print(f" {v:>10}", end="")
    print()
    for v1 in keys:
        print(f"{v1:>12}", end="")
        for v2 in keys:
            if v1 == v2:
                print(f" {'---':>10}", end="")
                continue
            if (v1, v2) in h2h:
                print(f" {h2h[(v1,v2)]['elo_a']:>9.1%}", end="")
            elif (v2, v1) in h2h:
                print(f" {h2h[(v2,v1)]['elo_b']:>9.1%}", end="")
        print()
    print()

    # ── Save results for phase 3 ──
    results = {
        'bench_scores': bench_scores,
        'h2h': {f"{a}_{b}": {k: v for k, v in h.items() if k not in ('a_scores', 'b_scores')} for (a, b), h in h2h.items()},
        'h2h_scores': {f"{a}_{b}": {'a': h['a_scores'], 'b': h['b_scores']} for (a, b), h in h2h.items()},
        'num_games': NUM,
    }
    with open('scratch/report_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Results saved to scratch/report_results.json")

if __name__ == "__main__":
    main()
