"""Verify shop selection is deterministic: run same seed twice and compare shops."""
import random, sys, os
sys.path.insert(0, '.')

# Reproduce the engine's shop selection logic
SHOPS = sorted(["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", 
                "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"])
MAX_SHOP_INSTANCES = 8
SHOP_INTERVAL = 3

def simulate_shops(seed, num_days=30):
    """Simulate shop unlocks for a given seed."""
    shops = []
    for day in range(num_days + 1):
        next_day = day
        if next_day > 0 and next_day % SHOP_INTERVAL == 0:
            if len(shops) < MAX_SHOP_INSTANCES:
                rng = random.Random((seed * 1_000_003) ^ next_day)
                shop = rng.choice(SHOPS)
                shops.append((next_day, shop))
    return shops

# Test seed 7
print("=== Seed 7 shop simulation ===")
shops_7 = simulate_shops(7)
for day, shop in shops_7:
    print(f"  Day {day}: {shop}")

# Test seed 0
print("\n=== Seed 0 shop simulation ===")
shops_0 = simulate_shops(0)
for day, shop in shops_0:
    print(f"  Day {day}: {shop}")

# Verify determinism: run seed 7 twice
print("\n=== Determinism check (seed 7) ===")
shops_7a = simulate_shops(7)
shops_7b = simulate_shops(7)
print(f"  Same? {shops_7a == shops_7b}")

# Now check: does the agent's opening affect the RNG state?
# The RNG is created fresh each time with (seed * 1_000_003) ^ day
# So the opening should NOT affect shop selection

# But wait - the engine uses env.info["seed"], not the configuration seed
# Let me check if env.info["seed"] is set correctly
from kaggle_environments import make
env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 7})
env.reset()
print(f"\n=== env.info['seed'] ===")
print(f"  {env.info.get('seed', 'NOT SET')}")

# Run again
env2 = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 7})
env2.reset()
print(f"  Run 2: {env2.info.get('seed', 'NOT SET')}")

# Check town state after reset
obs = env.state[0].observation
town = obs.get('town', {})
print(f"  Town after reset: {town}")

# Run one step to trigger day boundary
obs = env.state[0].observation
action = {"farmer": ["PASS"], "hands": [], "market": []}
env.step([action, action])
obs2 = env.state[0].observation
town2 = obs2.get('town', {})
print(f"  Town after step 0: {town2}")
