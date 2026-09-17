"""Analyze freed market slots and what reactive layers can do with them."""
import json, base64, gzip, zlib, copy, sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')
from notebook_analysis import build_agent_with_opening, load_route_data, load_notebook_agent

route_data = load_route_data()
agent_fn = build_agent_with_opening('c9', route_data)

# Get the internal route data
source = load_notebook_agent().replace('\r\n', '\n')
ns = {'__builtins__': __builtins__}
exec(compile(source, '<agent>', 'exec'), ns)
impl = ns['_IMPL']
chassis = impl.chassis

# Check what the routes plan for steps 0-10
print("=== Route analysis: steps 0-10 ===\n")
for route_id in sorted(chassis.routes.keys())[:5]:  # First 5 routes
    tape = chassis.routes[route_id]
    print(f"Route {route_id}:")
    for step in range(min(11, len(tape))):
        action = tape[step]
        if not isinstance(action, dict):
            continue
        market = action.get('market', [])
        farmer = action.get('farmer', [])
        hands = action.get('hands', [])
        if market or step < 3:
            print(f"  Step {step:>2}: market={market}  farmer={farmer}  hands={len(hands)}")
    print()

# Now run the agent for 10 steps and capture what it does
from kaggle_environments import make
env = make("kaggriculture", configuration={"episodeSteps": 720})
env.reset()

print("=== Agent actions for first 10 steps ===\n")
for step in range(10):
    obs = copy.deepcopy(env.state[0].observation)
    action = agent_fn(obs)
    market = action.get('market', [])
    farmer = action.get('farmer', [])
    print(f"Step {step:>2}: market={market}  farmer={farmer}")
    env.step([action, {"farmer": ["PASS"], "hands": [], "market": []}])

# Check what sell_lead would do on steps 0-1
print("\n=== Sell_lead analysis ===\n")
from notebook_analysis import load_notebook_agent
source = load_notebook_agent().replace('\r\n', '\n')
ns2 = {'__builtins__': __builtins__}
exec(compile(source, '<agent>', 'exec'), ns2)
impl2 = ns2['_IMPL']
chassis2 = impl2.chassis

# Get the route that was selected
env2 = make("kaggriculture", configuration={"episodeSteps": 720})
env2.reset()
obs = copy.deepcopy(env2.state[0].observation)
action = agent_fn(obs)
player = int(obs.get('player', 0))
st = chassis2.players.get(player, {})
route = st.get('route', None)
print(f"Selected route: {route}")

if route and route in chassis2.routes:
    tape = chassis2.routes[route]
    print(f"\nRoute {route} plans for steps 0-5:")
    for step in range(min(6, len(tape))):
        a = tape[step]
        if isinstance(a, dict):
            sells = [o for o in a.get('market', []) if o and o[0] == 'SELL']
            print(f"  Step {step}: SELLs = {sells}")

    print(f"\nsell_lead on step 0:")
    print(f"  Checks step % 4 == 0? step=0, 0%4=0, SKIP (returns early)")
    print(f"\nsell_lead on step 1:")
    print(f"  Checks step % 4 == 0? step=1, 1%4=1, CONTINUES")
    print(f"  Looks at step 2's planned SELLs")
    if len(tape) > 2:
        step2_sells = [o for o in tape[2].get('market', []) if o and o[0] == 'SELL']
        print(f"  Step 2 planned SELLs: {step2_sells}")
        if step2_sells:
            print(f"  -> sell_lead WOULD fire on step 1, selling items planned for step 2")
        else:
            print(f"  -> sell_lead would NOT fire (no planned sells on step 2)")

print(f"\nsell_lead on step 2:")
print(f"  Checks step % 4 == 0? step=2, 2%4=2, CONTINUES")
if len(tape) > 3:
    step3_sells = [o for o in tape[3].get('market', []) if o and o[0] == 'SELL']
    print(f"  Step 3 planned SELLs: {step3_sells}")

# Check budget_guard
print(f"\n=== Budget guard analysis ===")
print(f"budget_guard: 'fund each 72-step block's purchases'")
print(f"  On steps 0-1, budget_guard could buy seeds/animals not in the route")
print(f"  But it only prevents overspending, doesn't add purchases")

# Check what dead_stock does
print(f"\n=== Dead stock analysis ===")
print(f"dead_stock: 'sell stock the route will never sell'")
print(f"  On steps 0-1, dead_stock could sell items in the shed that the route never sells")
print(f"  This is the best use of freed slots: sell excess inventory immediately")
