"""Analyze route economics and identify improvement opportunities."""
import json
import sys
import os

sys.path.insert(0, '.')

def load_agent():
    """Load the V43+C9 agent."""
    with open('submission.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(compile(code, 'submission.py', 'exec'), globals())
    return globals()

def analyze_route_economics():
    """Analyze each route's economic characteristics."""
    g = load_agent()
    
    routes = g['_ROUTES']
    shop_routes = g['_R108_SHOP_ROUTES']
    old_shops = g['_R110_OLD_SHOPS']
    bakery_routes = g['_PIPE3_BAKERY_ROUTES']
    
    print(f"Total routes: {len(routes)}")
    print(f"BAKERY_ROUTES: {len(bakery_routes)}")
    
    # Analyze each route
    route_stats = []
    for route_id, tape in routes.items():
        if route_id not in routes:
            continue
        
        # Count action types
        market_actions = 0
        animal_actions = 0
        building_actions = 0
        movement_actions = 0
        
        for step in tape:
            if isinstance(step, dict):
                # Market actions
                if 'market' in step and step['market']:
                    for action in step['market']:
                        if isinstance(action, list) and len(action) > 0:
                            if action[0].startswith('BUY_') or action[0] == 'SELL':
                                market_actions += 1
                
                # Farmer actions
                if 'farmer' in step and step['farmer']:
                    for action in step['farmer']:
                        if isinstance(action, str):
                            if 'BUILD' in action or 'PLANT' in action:
                                building_actions += 1
                            elif 'BUY_ANIMAL' in action or 'PLACE_ANIMAL' in action:
                                animal_actions += 1
                            elif action.startswith('MOVE_'):
                                movement_actions += 1
                
                # Hand actions
                if 'hands' in step and step['hands']:
                    for hand_action in step['hands']:
                        if isinstance(hand_action, list) and len(hand_action) > 0:
                            if hand_action[0] == 'BUY_ANIMAL' or hand_action[0] == 'PLACE_ANIMAL':
                                animal_actions += 1
                            elif 'BUILD' in hand_action[0] or 'PLANT' in hand_action[0]:
                                building_actions += 1
                            elif hand_action[0].startswith('MOVE_'):
                                movement_actions += 1
        
        # Find which shop pair maps to this route
        shop_pair = None
        for pair, rid in shop_routes.items():
            if rid == route_id:
                shop_pair = pair
                break
        
        route_stats.append({
            'route_id': route_id,
            'total_steps': len(tape),
            'market_actions': market_actions,
            'animal_actions': animal_actions,
            'building_actions': building_actions,
            'movement_actions': movement_actions,
            'shop_pair': shop_pair,
            'is_bakery': route_id in bakery_routes
        })
    
    # Sort by route_id
    route_stats.sort(key=lambda x: x['route_id'])
    
    print("\nRoute characteristics:")
    print(f"{'Route':<8} {'Steps':<8} {'Market':<8} {'Animal':<8} {'Build':<8} {'Move':<8} {'Shop':<20} {'Bakery'}")
    print("-" * 100)
    for r in route_stats:
        shop_str = str(r['shop_pair']) if r['shop_pair'] else "None"
        print(f"{r['route_id']:<8} {r['total_steps']:<8} {r['market_actions']:<8} {r['animal_actions']:<8} {r['building_actions']:<8} {r['movement_actions']:<8} {shop_str:<20} {r['is_bakery']}")
    
    # Find routes with highest market activity
    print("\nTop 10 routes by market actions:")
    top_market = sorted(route_stats, key=lambda x: x['market_actions'], reverse=True)[:10]
    for r in top_market:
        print(f"  Route {r['route_id']}: {r['market_actions']} market actions, {r['animal_actions']} animal actions")
    
    # Find routes with highest animal activity
    print("\nTop 10 routes by animal actions:")
    top_animal = sorted(route_stats, key=lambda x: x['animal_actions'], reverse=True)[:10]
    for r in top_animal:
        print(f"  Route {r['route_id']}: {r['animal_actions']} animal actions, {r['market_actions']} market actions")
    
    return route_stats

if __name__ == '__main__':
    analyze_route_economics()
