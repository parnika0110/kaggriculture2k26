"""Analyze route selection in V43+C9 agent."""
import json
import sys
import os
import copy

sys.path.insert(0, '.')

def load_agent():
    """Load the V43+C9 agent."""
    with open('submission.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(compile(code, 'submission.py', 'exec'), globals())
    return globals()

def analyze_routes():
    """Analyze route selection and characteristics."""
    g = load_agent()
    
    # Get route data
    routes_data = g.get('_ROUTES', {})
    
    print(f"Total routes in V43+C9: {len(routes_data)}")
    
    # Analyze each route's structure
    route_stats = []
    for route_id, tape in routes_data.items():
        # Count action types
        actions = tape
        total_actions = len(actions)
        
        # Count market actions
        market_actions = sum(1 for a in actions if isinstance(a, str) and a.startswith('BUY_') or a.startswith('SELL_'))
        
        # Count building/farming actions
        building_actions = sum(1 for a in actions if isinstance(a, str) and ('BUILD' in a or 'PLANT' in a or 'WATER' in a))
        
        # Count animal actions
        animal_actions = sum(1 for a in actions if isinstance(a, str) and ('BUY_ANIMAL' in a or 'PLACE_ANIMAL' in a or 'FEED' in a or 'HARVEST' in a))
        
        # Count movement
        movement_actions = sum(1 for a in actions if isinstance(a, str) and a.startswith('MOVE_'))
        
        route_stats.append({
            'route_id': route_id,
            'total_actions': total_actions,
            'market_actions': market_actions,
            'building_actions': building_actions,
            'animal_actions': animal_actions,
            'movement_actions': movement_actions,
            'tape_preview': str(actions[:5]) + '...'
        })
    
    # Sort by total actions
    route_stats.sort(key=lambda x: x['total_actions'], reverse=True)
    
    print("\nRoute characteristics (sorted by total actions):")
    print(f"{'Route':<10} {'Total':<8} {'Market':<8} {'Build':<8} {'Animal':<8} {'Move':<8}")
    print("-" * 60)
    for r in route_stats[:20]:
        print(f"{r['route_id']:<10} {r['total_actions']:<8} {r['market_actions']:<8} {r['building_actions']:<8} {r['animal_actions']:<8} {r['movement_actions']:<8}")
    
    # Find BAKERY_ROUTES
    bakery_routes = g.get('_PIPE3_BAKERY_ROUTES', set())
    print(f"\nBAKERY_ROUTES: {len(bakery_routes)} routes")
    print(f"Route IDs: {sorted(bakery_routes)[:10]}...")
    
    # Check which routes are used in the agent
    # Look for route selection logic
    route_selection_code = []
    for name, val in g.items():
        if callable(val) and 'route' in name.lower():
            route_selection_code.append(name)
    
    print(f"\nRoute-related functions: {route_selection_code[:10]}")
    
    return route_stats

if __name__ == '__main__':
    analyze_routes()
