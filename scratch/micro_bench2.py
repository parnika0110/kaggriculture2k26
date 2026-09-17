import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission as v8_agent
import importlib.util
spec = importlib.util.spec_from_file_location("v7", os.path.join(os.path.dirname(__file__), "..", "submission_v7.py"))
v7_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7_mod)

def micro_bench():
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    
    # Collect observations
    env.reset()
    env.run([v7_mod.agent, "starter"])
    obs_list = []
    env.reset()
    while True:
        obs = env.state[0].observation
        obs_list.append(dict(obs))
        env.step([None, None])
        if env.done:
            break
    
    # Warm up
    for _ in range(100):
        v7_mod.agent(obs_list[100])
        v8_agent.agent(obs_list[100])
    
    # Benchmark in phases
    phases = [
        ("Early (0-120)", range(0, 120)),
        ("Mid (120-360)", range(120, 360)),
        ("Late (360-600)", range(360, 600)),
        ("End (600-719)", range(600, 719)),
    ]
    
    for name, indices in phases:
        v7s = []
        v8s = []
        for i in indices:
            if i >= len(obs_list):
                break
            obs = obs_list[i]
            
            # V7
            start = time.perf_counter_ns()
            v7_mod.agent(obs)
            v7s.append(time.perf_counter_ns() - start)
            
            # V8
            start = time.perf_counter_ns()
            v8_agent.agent(obs)
            v8s.append(time.perf_counter_ns() - start)
        
        avg7 = sum(v7s) / len(v7s) / 1000
        avg8 = sum(v8s) / len(v8s) / 1000
        p95_7 = sorted(v7s)[int(len(v7s)*0.95)] / 1000
        p95_8 = sorted(v8s)[int(len(v8s)*0.95)] / 1000
        print(f"{name:20s}: V7 avg={avg7:.1f}µs p95={p95_7:.1f}µs  V8 avg={avg8:.1f}µs p95={p95_8:.1f}µs  speed={avg7/avg8:.2f}x")
    
    # Overall
    v7all = []
    v8all = []
    for obs in obs_list:
        start = time.perf_counter_ns()
        v7_mod.agent(obs)
        v7all.append(time.perf_counter_ns() - start)
        start = time.perf_counter_ns()
        v8_agent.agent(obs)
        v8all.append(time.perf_counter_ns() - start)
    
    avg7 = sum(v7all) / len(v7all) / 1000
    avg8 = sum(v8all) / len(v8all) / 1000
    print(f"{'Overall':20s}: V7 avg={avg7:.1f}µs  V8 avg={avg8:.1f}µs  speed={avg7/avg8:.2f}x")

if __name__ == "__main__":
    micro_bench()
