"""Analyze what products each route trades."""
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

def analyze_route_products():
    """Analyze what products each route trades."""
    g = load_agent()
    
    routes = g['_ROUTES']
    
    # Analyze a few key routes
    key_routes = [0, 1, 2, 3, 101, 103, 104, 105, 106, 107, 108, 109, 111, 119, 120]
    
    for route_id in key_routes:
        if route_id not in routes:
            continue
        
        tape = routes[route_id]
        
        # Count products traded
        products_bought = {}
        products_sold = {}
        
        for step in tape:
            if isinstance(step, dict) and 'market' in step and step['market']:
                for action in step['market']:
                    if isinstance(action, list) and len(action) > 0:
                        if action[0] == 'BUY_PRODUCT' and len(action) > 2:
                            product = action[1]
                            qty = action[2] if len(action) > 2 else 1
                            products_bought[product] = products_bought.get(product, 0) + qty
                        elif action[0] == 'SELL' and len(action) > 2:
                            product = action[1]
                            qty = action[2] if len(action) > 2 else 1
                            products_sold[product] = products_sold.get(product, 0) + qty
        
        print(f"\nRoute {route_id}:")
        print(f"  Products bought: {dict(sorted(products_bought.items(), key=lambda x: x[1], reverse=True))}")
        print(f"  Products sold: {dict(sorted(products_sold.items(), key=lambda x: x[1], reverse=True))}")
        
        # Net position
        all_products = set(list(products_bought.keys()) + list(products_sold.keys()))
        net_position = {}
        for p in all_products:
            net_position[p] = products_sold.get(p, 0) - products_bought.get(p, 0)
        
        print(f"  Net position: {dict(sorted(net_position.items(), key=lambda x: x[1], reverse=True))}")

if __name__ == '__main__':
    analyze_route_products()
