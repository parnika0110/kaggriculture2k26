"""Analyze GOOSE economic contribution in V43+C9.

Trace: purchases, placement, feeding, harvesting, selling.
Compute net GOOSE contribution per route.
"""
import json, sys
sys.path.insert(0, '.')

base_globals = {}
exec(open('submission.py', encoding='utf-8').read(), base_globals)
base_agent = base_globals['agent']

from kaggle_environments import make

SEEDS = list(range(20))
CONFIG = {"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}

def analyze_game(seed):
    """Run one game and extract GOOSE economics."""
    cfg = dict(CONFIG); cfg["seed"] = seed
    env = make("kaggriculture", debug=True, configuration=cfg)
    trainer = env.train([None, "starter"])
    obs = trainer.reset()
    
    goose_purchases = 0
    goose_cost = 0
    egg_sales = 0
    egg_revenue = 0
    wheat_feeded_to_goose = 0
    wheat_cost_for_goose = 0
    
    # Track per-route statistics
    route_stats = {}  # route_id -> {goose_count, egg_revenue, goose_cost, feed_cost}
    
    # Track market inventory changes for GOOSE/EGG
    market_eggs_before = obs["market"]["inventory"].get("EGG", 10000)
    market_eggs_after = 0
    
    step = 0
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = base_agent(obs_json)
        
        # Analyze market orders
        market_orders = action.get("market", [])
        for order in market_orders:
            if isinstance(order, list) and len(order) >= 3:
                op = order[0]
                item = order[1]
                qty = int(order[2]) if isinstance(order[2], (int, float)) else 0
                
                if op == "BUY_ANIMAL" and item == "GOOSE":
                    goose_purchases += qty
                    goose_cost += qty * 300  # GOOSE costs $300
                elif op == "SELL" and item == "EGG":
                    egg_sales += qty
                elif op == "BUY_PRODUCT" and item == "WHEAT":
                    pass  # Could be for any animal
        
        # Check shed for EGG count changes
        shed = obs["private"]["shed"]
        eggs_in_shed = shed.get("EGG", 0)
        
        # Check farm tiles for GOOSEs
        farm = obs["farms"][0]
        goose_on_board = 0
        for row in farm["tiles"]:
            for tile in row:
                if isinstance(tile, dict) and tile.get("animal") == "GOOSE":
                    goose_on_board += 1
        
        obs, reward, done, info = trainer.step(action)
        step += 1
    
    # Final state
    final_shed = obs["private"]["shed"]
    final_eggs = final_shed.get("EGG", 0)
    market_eggs_after = obs["market"]["inventory"].get("EGG", 10000)
    
    # Count GOOSEs on final board
    final_farm = obs["farms"][0]
    final_goose = 0
    for row in final_farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") == "GOOSE":
                final_goose += 1
    
    return {
        "seed": seed,
        "score": reward,
        "goose_purchases": goose_purchases,
        "goose_cost": goose_cost,
        "egg_sales": egg_sales,
        "final_eggs_in_shed": final_eggs,
        "final_goose_on_board": final_goose,
        "market_eggs_consumed": market_eggs_before - market_eggs_after + egg_sales,
    }

# Run analysis
print("=" * 80)
print("GOOSE ECONOMIC ANALYSIS (20 seeds, V43+C9 vs starter)")
print("=" * 80)

results = []
for seed in SEEDS:
    r = analyze_game(seed)
    results.append(r)
    print(f"Seed {seed:2d}: score=${r['score']:>9,.0f}  "
          f"goose_buy={r['goose_purchases']} (${r['goose_cost']:>4,})  "
          f"egg_sell={r['egg_sales']}  "
          f"final_goose={r['final_goose_on_board']}  "
          f"final_eggs_shed={r['final_eggs_in_shed']}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

total_score = sum(r["score"] for r in results)
total_goose_cost = sum(r["goose_cost"] for r in results)
total_goose_bought = sum(r["goose_purchases"] for r in results)
total_egg_sold = sum(r["egg_sales"] for r in results)
total_final_goose = sum(r["final_goose_on_board"] for r in results)
total_final_eggs = sum(r["final_eggs_in_shed"] for r in results)

print(f"Mean score: ${total_score/len(results):,.0f}")
print(f"Total GOOSEs bought: {total_goose_bought} (${total_goose_cost:,})")
print(f"Mean GOOSEs per game: {total_goose_bought/len(results):.1f}")
print(f"Total EGGs sold: {total_egg_sold}")
print(f"Mean EGGs sold per game: {total_egg_sold/len(results):.1f}")
print(f"Mean final GOOSEs on board: {total_final_goose/len(results):.1f}")
print(f"Mean final EGGs in shed: {total_final_eggs/len(results):.1f}")
print(f"GOOSE cost per game: ${total_goose_cost/len(results):,.0f}")

# Estimate EGG revenue (need to run with tracking)
# For now, estimate based on market prices
# EGG base price = $50, first yield day 4, interval 1
# A GOOSE produces 1 EGG/day from day 4 to day 29 = 26 days
# But max_held = 4, so need to harvest regularly
# Estimated EGG revenue per GOOSE: ~$50 * 20 harvests = $1,000
# Net per GOOSE: $1,000 - $300 (purchase) - $250 (30 days wheat feed) = $450
# But this is rough - need actual data

print(f"\nEstimated economics per GOOSE:")
print(f"  Purchase cost: $300")
print(f"  Feed cost (30 days x $25): ~$750")
print(f"  Total cost: ~$1,050")
print(f"  Estimated EGG revenue (20 harvests x $50): ~$1,000")
print(f"  Estimated net: ~-$50 (GOOSE may be net negative!)")
print(f"\n  NOTE: This is a rough estimate. Need actual revenue tracking.")
