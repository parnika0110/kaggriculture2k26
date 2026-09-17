"""Analyze V43+C9 actual production across seeds."""
import sys, json, os
sys.path.insert(0, '.')

# Must load before import submission
from kaggle_environments import make

# Load the agent
exec(open('submission.py', encoding='utf-8').read())

def analyze_game(seed):
    """Run one game and extract detailed production stats."""
    env = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720,
        "boardSize": 10,
        "turnsPerDay": 24,
        "shedCapacity": 100,
        "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1,
        "seed": seed,
    })
    trainer = env.train([None, "random"])
    obs = trainer.reset()
    
    step = 0
    total_harvested = {}
    total_sold = {}
    total_built = {"COOP": 0, "PASTURE": 0}
    total_placed = {"GOOSE": 0, "COW": 0, "SHEEP": 0}
    total_planted = {}
    money_history = []
    day_history = []
    
    done = False
    while not done:
        obs_json = json.loads(json.dumps(obs))
        action = agent(obs_json)
        obs, reward, done, info = trainer.step(action)
        step += 1
        
        # Track money every 24 steps (end of day)
        if step % 24 == 0:
            money_history.append(obs['farms'][0]['money'])
            day_history.append(obs['day'])
    
    # Final state analysis
    farm = obs['farms'][0]
    private = obs['private']
    tiles = farm['tiles']
    
    # Count tiles
    animals_on_board = {"COOP": 0, "PASTURE": 0, "GOOSE": 0, "COW": 0, "SHEEP": 0}
    plants_on_board = {}
    structures_empty = {"COOP": 0, "PASTURE": 0}
    empty_tiles = 0
    locked_tiles = 0
    
    for row in tiles:
        for tile in row:
            if tile is None:
                empty_tiles += 1
            elif tile == "LOCKED":
                locked_tiles += 1
            elif isinstance(tile, dict):
                kind = tile.get("kind", "")
                if "animal" in tile:
                    animal = tile["animal"]
                    animals_on_board[animal] = animals_on_board.get(animal, 0) + 1
                    animals_on_board[kind] = animals_on_board.get(kind, 0) + 1
                elif kind == "PLANT":
                    crop = tile["crop"]
                    plants_on_board[crop] = plants_on_board.get(crop, 0) + 1
                elif kind in ("COOP", "PASTURE"):
                    structures_empty[kind] = structures_empty.get(kind, 0) + 1
                elif kind == "WEED":
                    pass
    
    # Shed contents
    shed = private.get("shed", {})
    seeds = private.get("seeds", {})
    
    # Market actions from agent telemetry
    telemetry = getattr(agent, 'telemetry', {})
    
    result = {
        "seed": seed,
        "final_score": farm['money'],
        "final_day": obs.get('day', 0),
        "unlocked": farm['unlocked_quadrants'],
        "animals_on_board": {k: v for k, v in animals_on_board.items() if v > 0},
        "plants_on_board": plants_on_board,
        "structures_empty": structures_empty,
        "empty_tiles": empty_tiles,
        "locked_tiles": locked_tiles,
        "shed": dict(shed),
        "seeds": dict(seeds),
        "hands_count": len(farm.get("hands", [])),
        "money_day10": money_history[10] if len(money_history) > 10 else None,
        "money_day20": money_history[20] if len(money_history) > 20 else None,
        "money_day29": money_history[29] if len(money_history) > 29 else None,
        "telemetry": telemetry,
    }
    return result

def format_analysis(result):
    """Pretty-print the analysis."""
    print(f"\n{'='*60}")
    print(f"  SEED {result['seed']}")
    print(f"{'='*60}")
    print(f"  Final Score: ${result['final_score']:,.0f}")
    print(f"  Final Day: {result['final_day']}")
    print(f"  Unlocked Quadrants: {result['unlocked']}")
    print(f"  Hands: {result['hands_count']}")
    print()
    
    print(f"  Animals on Board:")
    for animal, count in result['animals_on_board'].items():
        if animal in ('COOP', 'PASTURE'):
            continue
        print(f"    {animal}: {count}")
    empty = result['structures_empty']
    if empty:
        print(f"  Empty Structures: COOP={empty.get('COOP', 0)}, PASTURE={empty.get('PASTURE', 0)}")
    print()
    
    print(f"  Crops on Board:")
    for crop, count in result['plants_on_board'].items():
        print(f"    {crop}: {count}")
    print(f"  Empty Tiles: {result['empty_tiles']}")
    print(f"  Locked Tiles: {result['locked_tiles']}")
    print()
    
    print(f"  Shed: {result['shed']}")
    print(f"  Seeds: {result['seeds']}")
    print()
    
    print(f"  Money Trajectory:")
    print(f"    Day 10: ${result['money_day10']:,.0f}" if result['money_day10'] else "    Day 10: N/A")
    print(f"    Day 20: ${result['money_day20']:,.0f}" if result['money_day20'] else "    Day 20: N/A")
    print(f"    Day 29: ${result['money_day29']:,.0f}" if result['money_day29'] else "    Day 29: N/A")
    
    if result['telemetry']:
        print(f"\n  Telemetry:")
        for k, v in result['telemetry'].items():
            if isinstance(v, int) and v > 0:
                print(f"    {k}: {v}")

if __name__ == "__main__":
    seeds = [0, 1, 5, 7, 42]
    results = []
    for seed in seeds:
        print(f"Running seed {seed}...")
        r = analyze_game(seed)
        results.append(r)
        format_analysis(r)
    
    # Summary
    scores = [r['final_score'] for r in results]
    print(f"\n{'='*60}")
    print(f"  SUMMARY ({len(results)} games)")
    print(f"{'='*60}")
    print(f"  Mean Score: ${sum(scores)/len(scores):,.0f}")
    print(f"  Min Score: ${min(scores):,.0f}")
    print(f"  Max Score: ${max(scores):,.0f}")
    print(f"  Median: ${sorted(scores)[len(scores)//2]:,.0f}")
    
    # Animal counts
    all_animals = {}
    for r in results:
        for animal, count in r['animals_on_board'].items():
            if animal in ('COOP', 'PASTURE'):
                continue
            all_animals[animal] = all_animals.get(animal, 0) + count
    print(f"\n  Average Animals (across {len(results)} games):")
    for animal, total in sorted(all_animals.items()):
        print(f"    {animal}: {total/len(results):.1f}")
    
    # Plant counts
    all_plants = {}
    for r in results:
        for crop, count in r['plants_on_board'].items():
            all_plants[crop] = all_plants.get(crop, 0) + count
    print(f"\n  Average Plants (across {len(results)} games):")
    for crop, total in sorted(all_plants.items()):
        print(f"    {crop}: {total/len(results):.1f}")
