import sys, os, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kaggle_environments import make
import submission as v9
import importlib.util

spec = importlib.util.spec_from_file_location('v7', os.path.join(os.path.dirname(__file__), '..', 'submission_v7.py'))
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)

env = make('kaggriculture', configuration={'episodeSteps': 720})

for ep in range(10):
    env.reset()
    env.run([v7.agent, 'starter'])
    r7 = env.steps[-1][0].reward
    env.reset()
    env.run([v9.agent, 'starter'])
    r9 = env.steps[-1][0].reward
    print(f'Ep {ep+1}: V7=${r7:.0f}  V9=${r9:.0f}  diff=${r9-r7:+.0f}')

v7s = []; v9s = []
for ep in range(20):
    env.reset()
    env.run([v7.agent, 'starter'])
    v7s.append(env.steps[-1][0].reward)
    env.reset()
    env.run([v9.agent, 'starter'])
    v9s.append(env.steps[-1][0].reward)
print(f'\n20-ep avg: V7=${sum(v7s)/len(v7s):.0f}  V9=${sum(v9s)/len(v9s):.0f}')
print(f'V9 wins: {sum(1 for a,b in zip(v7s,v9s) if b>=a)}/20')
