"""Deep comparison: analyze what V7's unique features contribute."""
import json, sys
sys.path.insert(0, '.')

# Load both agents
v43_globals = {}
exec(open('submission.py', encoding='utf-8').read(), v43_globals)
v43_agent = v43_globals['agent']

v7_globals = {}
exec(open('scratch/v7_agent.py', encoding='utf-8').read(), v7_globals)
v7_agent = v7_globals['agent']

# Compare the key unique V7 features
print("=" * 70)
print("V7 UNIQUE FEATURES ANALYSIS")
print("=" * 70)

# 1. Check if V7 has race detection
print("\n1. Race detection (_race_* functions):")
print("   These detect competitive market situations and adjust strategy.")
race_funcs = [k for k in v7_globals if k.startswith('_race_')]
print(f"   Functions: {race_funcs}")

# 2. Check frontload/advance_sales
print("\n2. Market simulation (frontload/advance_sales):")
frontload_exists = 'frontload' in v7_globals
advance_exists = 'advance_sales' in v7_globals
print(f"   frontload: {frontload_exists}")
print(f"   advance_sales: {advance_exists}")

# 3. Check r60 survival guard
print("\n3. Survival guard (_r60_*):")
r60_funcs = [k for k in v7_globals if k.startswith('_r60_')]
print(f"   Functions: {r60_funcs}")

# 4. Compare the agent wrapper chains
print("\n4. Agent wrapper chains (outermost -> innermost):")
# Both agents use the same pattern: each layer wraps the previous

# 5. Check opening differences
print("\n5. Opening comparison:")
# Both should have _PIPE3_BAKERY_ROUTES
v43_has_bakery = '_PIPE3_BAKERY_ROUTES' in v43_globals
v7_has_bakery = '_PIPE3_BAKERY_ROUTES' in v7_globals
print(f"   V43+C9 BAKERY_ROUTES: {v43_has_bakery}")
print(f"   V7 BAKERY_ROUTES: {v7_has_bakery}")

# 6. Compare the final agent function behavior on a test seed
print("\n6. Action comparison on seed 0:")
from kaggle_environments import make

for seed in [0, 5, 7, 18]:  # Seeds where V7 wins and loses
    env = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": seed,
    })
    trainer = env.train([None, "random"])
    obs = trainer.reset()
    done = False
    
    v43_market_total = 0
    v7_market_total = 0
    v43_pass_total = 0
    v7_pass_total = 0
    step = 0
    
    while not done:
        obs_json = json.loads(json.dumps(obs))
        a43 = v43_agent(obs_json)
        a7 = v7_agent(obs_json)
        
        # Count market orders
        v43_market_total += len(a43.get('market', []))
        v7_market_total += len(a7.get('market', []))
        
        # Count PASS actions
        v43_acts = [a43.get('farmer', ['PASS'])] + a43.get('hands', [])
        v7_acts = [a7.get('farmer', ['PASS'])] + a7.get('hands', [])
        v43_pass_total += sum(1 for a in v43_acts if a == ['PASS'] or not a)
        v7_pass_total += sum(1 for a in v7_acts if a == ['PASS'] or not a)
        
        # Run V43's game
        obs, reward, done, info = trainer.step(a43)
        step += 1
    
    # Run V7 separately to get its score
    env2 = make("kaggriculture", debug=True, configuration={
        "episodeSteps": 720, "boardSize": 10, "turnsPerDay": 24,
        "shedCapacity": 100, "maxMarketOrdersPerTurn": 10,
        "farmHandCostMult": 1, "seed": seed,
    })
    trainer2 = env2.train([None, "random"])
    obs2 = trainer2.reset()
    done2 = False
    while not done2:
        obs_json2 = json.loads(json.dumps(obs2))
        a7 = v7_agent(obs_json2)
        obs2, reward7, done2, info2 = trainer2.step(a7)
    
    print(f"\n   Seed {seed}:")
    print(f"     V43 score: ${reward:,.0f}  V7 score: ${reward7:,.0f}")
    print(f"     V43 market orders: {v43_market_total}  V7: {v7_market_total} (diff: {v7_market_total-v43_market_total:+d})")
    print(f"     V43 PASS actions: {v43_pass_total}  V7: {v7_pass_total} (diff: {v7_pass_total-v43_pass_total:+d})")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
V7 adds these capabilities on top of V43+C9:
1. Race detection: Adjusts strategy in competitive games
2. Market simulation: frontload() and advance_sales() optimize sale timing
3. Survival guard (_r60): Prevents bankruptcy in tight economies
4. Opening liquidity (_r60_opening_liquidity): Better early-game cash flow

However, V7 is only +1.3% better on average (10/20 wins).
The improvements are marginal and inconsistent.

To make V43+C9 beat V7 in ALL aspects, we should:
1. Port V7's best features (survival guard, market simulation)
2. Fix V7's weaknesses (seeds where V43 wins by $20K+)
3. Add V7's missing optimizations
""")
