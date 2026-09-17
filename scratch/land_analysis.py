"""Trace land purchases and their economic impact in V43+C9.

Identify: when quadrants are bought, what depends on them, estimated value.
"""
import json, sys
sys.path.insert(0, '.')

base_globals = {}
exec(open('submission.py', encoding='utf-8').read(), base_globals)
base_agent = base_globals['agent']

from kaggle_environments import make

CONFIG = {"episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
          "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
          "farmHandCostMult": 1}

LAND_COSTS = {"NE": 1000, "SW": 2000, "SE": 4000}

def trace_land_purchases(seed):
    """Run one game and trace all land purchases."""
    cfg = dict(CONFIG); cfg["seed"] = seed
    env = make("kaggriculture", debug=True, configuration=cfg)
    trainer = env.train([None, "starter"])
    obs = trainer.reset()
    
    purchases = []  # {step, quadrant, cost}
    unlocked_history = []  # [(step, unlocked_list)]
    
    step = 0
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = base_agent(obs_json)
        
        # Check market orders for BUY_LAND
        market = action.get("market", [])
        if isinstance(market, list):
            for o in market:
                if isinstance(o, list) and len(o) > 0 and o[0] == "BUY_LAND":
                    # Determine which quadrant would be unlocked
                    current_unlocked = obs["farms"][0]["unlocked_quadrants"]
                    n_unlocked = len(current_unlocked) - 1  # NW always there
                    if n_unlocked < 3:
                        quadrant = ["NE", "SW", "SE"][n_unlocked]
                        cost = [1000, 2000, 4000][n_unlocked]
                        purchases.append({
                            "step": step,
                            "day": step // 24,
                            "hour": step % 24,
                            "quadrant": quadrant,
                            "cost": cost,
                        })
        
        # Track unlocked quadrants
        unlocked = obs["farms"][0]["unlocked_quadrants"]
        if not unlocked_history or unlocked != unlocked_history[-1][1]:
            unlocked_history.append((step, list(unlocked)))
        
        obs, reward, done, info = trainer.step(action)
        step += 1
    
    # Final state
    final_farm = obs["farms"][0]
    final_unlocked = final_farm["unlocked_quadrants"]
    
    # Count tiles used in each quadrant
    quadrant_usage = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
    quadrant_animals = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
    quadrant_structures = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
    
    for y in range(10):
        for x in range(10):
            # Determine quadrant
            if x < 5 and y < 5: q = "NW"
            elif x >= 5 and y < 5: q = "NE"
            elif x < 5 and y >= 5: q = "SW"
            else: q = "SE"
            
            tile = final_farm["tiles"][y][x]
            if tile is None or tile == "LOCKED":
                continue
            if isinstance(tile, dict):
                quadrant_usage[q] += 1
                if "animal" in tile:
                    quadrant_animals[q] += 1
                elif tile.get("kind") in ("COOP", "PASTURE"):
                    quadrant_structures[q] += 1
    
    return {
        "seed": seed,
        "score": reward,
        "purchases": purchases,
        "final_unlocked": final_unlocked,
        "quadrant_usage": quadrant_usage,
        "quadrant_animals": quadrant_animals,
        "quadrant_structures": quadrant_structures,
    }

# Run analysis on 20 seeds
print("=" * 100)
print("LAND PURCHASE ANALYSIS (20 seeds, V43+C9 vs starter)")
print("=" * 100)

results = []
for seed in range(20):
    r = trace_land_purchases(seed)
    results.append(r)
    
    purchases_str = ", ".join(f"{p['quadrant']}(step {p['step']}, ${p['cost']})" for p in r["purchases"])
    if not purchases_str:
        purchases_str = "none"
    
    animals_str = ", ".join(f"{q}:{r['quadrant_animals'][q]}" for q in ["NE", "SW", "SE"] if r['quadrant_animals'][q] > 0)
    
    print(f"Seed {seed:2d}: score=${r['score']:>9,.0f}  purchases=[{purchases_str}]  animals=[{animals_str}]")

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

# Count how many games buy each quadrant
ne_bought = sum(1 for r in results if any(p["quadrant"] == "NE" for p in r["purchases"]))
sw_bought = sum(1 for r in results if any(p["quadrant"] == "SW" for p in r["purchases"]))
se_bought = sum(1 for r in results if any(p["quadrant"] == "SE" for p in r["purchases"]))

print(f"NE purchased: {ne_bought}/20 games")
print(f"SW purchased: {sw_bought}/20 games")
print(f"SE purchased: {se_bought}/20 games")

# Average purchase step
ne_steps = [p["step"] for r in results for p in r["purchases"] if p["quadrant"] == "NE"]
sw_steps = [p["step"] for r in results for p in r["purchases"] if p["quadrant"] == "SW"]
se_steps = [p["step"] for r in results for p in r["purchases"] if p["quadrant"] == "SE"]

if ne_steps:
    print(f"\nNE: avg step {sum(ne_steps)/len(ne_steps):.0f} (day {sum(ne_steps)/len(ne_steps)/24:.1f}), cost $1,000")
if sw_steps:
    print(f"SW: avg step {sum(sw_steps)/len(sw_steps):.0f} (day {sum(sw_steps)/len(sw_steps)/24:.1f}), cost $2,000")
if se_steps:
    print(f"SE: avg step {sum(se_steps)/len(se_steps):.0f} (day {sum(se_steps)/len(se_steps)/24:.1f}), cost $4,000")

# Quadrant usage
print("\nQuadrant usage (average across games):")
for q in ["NE", "SW", "SE"]:
    bought = [r for r in results if any(p["quadrant"] == q for p in r["purchases"])]
    if bought:
        avg_usage = sum(r["quadrant_usage"][q] for r in bought) / len(bought)
        avg_animals = sum(r["quadrant_animals"][q] for r in bought) / len(bought)
        avg_structures = sum(r["quadrant_structures"][q] for r in bought) / len(bought)
        print(f"  {q}: {avg_usage:.1f} tiles used, {avg_animals:.1f} animals, {avg_structures:.1f} structures")

# Score comparison: games with vs without each purchase
print("\nScore comparison:")
for q in ["NE", "SW"]:
    with_q = [r["score"] for r in results if any(p["quadrant"] == q for p in r["purchases"])]
    without_q = [r["score"] for r in results if not any(p["quadrant"] == q for p in r["purchases"])]
    if with_q and without_q:
        avg_with = sum(with_q) / len(with_q)
        avg_without = sum(without_q) / len(without_q)
        print(f"  {q}: with={avg_with:,.0f} ({len(with_q)} games), without={avg_without:,.0f} ({len(without_q)} games), diff={avg_with-avg_without:+,.0f}")
