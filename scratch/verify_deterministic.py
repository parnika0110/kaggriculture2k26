"""Verify deterministic shop selection matches engine exactly."""
import random, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')

SHOPS = sorted(["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", 
                "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"])
MAX_SHOP_INSTANCES = 8
SHOP_INTERVAL = 3

def simulate_shops(seed, num_days=30):
    """Simulate shop unlocks matching engine logic exactly."""
    shops = []
    for day in range(num_days):
        next_day = day + 1
        if next_day > 0 and next_day % SHOP_INTERVAL == 0:
            if len(shops) < MAX_SHOP_INSTANCES:
                rng = random.Random((seed * 1_000_003) ^ next_day)
                shop = rng.choice(SHOPS)
                shops.append((next_day, shop))
    return shops

# Test multiple seeds
for seed in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
    shops = simulate_shops(seed)
    first_3 = [s for _, s in shops[:3]]
    print(f"Seed {seed:>2}: {first_3}")

print(f"\n--- Seed 7 full shop list ---")
for day, shop in simulate_shops(7):
    print(f"  Day {day}: {shop}")

print(f"\n--- Seed 0 full shop list ---")
for day, shop in simulate_shops(0):
    print(f"  Day {day}: {shop}")
