"""Extract the V43+C9 agent from the notebook and analyze its reactive layers."""
import json, base64, gzip, sys, os, re
sys.path.insert(0, '.')
sys.path.insert(0, 'scratch')

def extract_agent():
    nb_path = os.path.join('.', 'beyond-v43-what-the-top-clusters-do-on-turn-1 (1).ipynb')
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    for s in nb['cells'][7]['source']:
        if 'B85_SOURCE' in s and 'ABzY8' in s:
            idx = s.find("B85_SOURCE = '") + len("B85_SOURCE = '")
            b85 = s[idx:].rstrip('\n').rstrip("'")
            raw = base64.b85decode(b85)
            source = gzip.decompress(raw).decode('utf-8', errors='replace')
            return source
    raise ValueError('B85_SOURCE not found')

source = extract_agent()
# Normalize
source = source.replace('\r\n', '\n')

# Save full source
with open('submission_v43c9.py', 'w', encoding='utf-8') as f:
    f.write(source)
print(f"Agent source saved: {len(source)} chars, {source.count(chr(10))} lines")

# Analyze reactive layers
layers = ['hand_align', 'weed_repair', 'sell_lead', 'front_run', 'budget_guard', 
          'room_guard', 'clamp_sells', 'dead_stock', 'terminal_liquidation']
for layer in layers:
    count = source.count(layer)
    print(f"  {layer}: {count} references")

# Check which layers are enabled in DEFAULT_SETTINGS
settings_match = re.search(r'DEFAULT_SETTINGS\s*=\s*\{([^}]+)\}', source)
if settings_match:
    print(f"\nDEFAULT_SETTINGS block found ({len(settings_match.group(0))} chars)")
    # Extract enabled/disabled
    for layer in layers:
        m = re.search(rf'"{layer}":\s*(True|False)', settings_match.group(0))
        if m:
            print(f"  {layer}: {'ENABLED' if m.group(1) == 'True' else 'DISABLED'}")

# Analyze what happens on steps 0-10
print("\n--- Analyzing steps 0-10 in the chassis ---")
# Find the act() method and reactive layer calls
act_match = re.search(r'def act\(self.*?\n(?:    def |\nclass )', source, re.DOTALL)
if act_match:
    act_body = act_match.group(0)
    print(f"act() method: {len(act_body)} chars")
    # Count layer calls in act()
    for layer in layers:
        if layer in act_body:
            print(f"  {layer} called in act()")

# Check for any step-specific logic (step < 10, step == 0, etc.)
step_checks = re.findall(r'step\s*[<>=!]+\s*\d+', source)
print(f"\nStep checks found: {len(step_checks)}")
for s in set(step_checks):
    print(f"  {s}")

# Check sell_lead implementation
sell_lead_match = re.search(r'def _sell_lead\(.*?\n    def ', source, re.DOTALL)
if sell_lead_match:
    print(f"\n_sell_lead method: {len(sell_lead_match.group(0))} chars")
    print(sell_lead_match.group(0)[:500])
