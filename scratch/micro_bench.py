import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission as v8_agent

# Import V7
import importlib.util
spec = importlib.util.spec_from_file_location("v7", os.path.join(os.path.dirname(__file__), "..", "submission_v7.py"))
v7_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7_mod)

def micro_bench(n_runs=3):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    
    # Collect observations from a real game
    env.reset()
    env.run([v7_mod.agent, "starter"])
    
    # Replay and collect observations
    obs_list = []
    env.reset()
    while True:
        obs = env.state[0].observation
        obs_list.append(dict(obs))  # deep copy
        env.step([None, None])  # advance one step
        if env.done:
            break
    
    print(f"Collected {len(obs_list)} observations from a real game")
    
    # Warm up
    for _ in range(50):
        v7_mod.agent(obs_list[100])
        v8_agent.agent(obs_list[100])
    
    # Benchmark V7
    times_v7 = []
    for obs in obs_list:
        start = time.perf_counter_ns()
        v7_mod.agent(obs)
        elapsed = time.perf_counter_ns() - start
        times_v7.append(elapsed)
    
    # Benchmark V8
    times_v8 = []
    for obs in obs_list:
        start = time.perf_counter_ns()
        v8_agent.agent(obs)
        elapsed = time.perf_counter_ns() - start
        times_v8.append(elapsed)
    
    # Stats
    times_v7_us = [t / 1000 for t in times_v7]
    times_v8_us = [t / 1000 for t in times_v8]
    
    avg_v7 = sum(times_v7_us) / len(times_v7_us)
    avg_v8 = sum(times_v8_us) / len(times_v8_us)
    
    print(f"\nV7 per-call (µs): min={min(times_v7_us):.1f}  avg={avg_v7:.1f}  p50={sorted(times_v7_us)[len(times_v7_us)//2]:.1f}  p95={sorted(times_v7_us)[int(len(times_v7_us)*0.95)]:.1f}  max={max(times_v7_us):.1f}")
    print(f"V8 per-call (µs): min={min(times_v8_us):.1f}  avg={avg_v8:.1f}  p50={sorted(times_v8_us)[len(times_v8_us)//2]:.1f}  p95={sorted(times_v8_us)[int(len(times_v8_us)*0.95)]:.1f}  max={max(times_v8_us):.1f}")
    print(f"\nSpeedup: {avg_v7/avg_v8:.2f}x")
    print(f"V7 total: {sum(times_v7_us)/1000:.2f}ms for {len(times_v7)} calls")
    print(f"V8 total: {sum(times_v8_us)/1000:.2f}ms for {len(times_v8)} calls")

if __name__ == "__main__":
    micro_bench()
