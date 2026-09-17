import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission as v8_agent

# Import original V7 from git
import importlib.util
spec = importlib.util.spec_from_file_location("v7", os.path.join(os.path.dirname(__file__), "..", "submission_v7.py"))
v7_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7_mod)

def compare(n=10):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    
    v7_scores = []
    v8_scores = []
    v7_times = []
    v8_times = []
    
    for ep in range(n):
        # V7
        env.reset()
        start = time.perf_counter()
        env.run([v7_mod.agent, "starter"])
        v7_t = time.perf_counter() - start
        v7_r = env.steps[-1][0].reward
        
        # V8 — same environment state after reset
        env.reset()
        start = time.perf_counter()
        env.run([v8_agent.agent, "starter"])
        v8_t = time.perf_counter() - start
        v8_r = env.steps[-1][0].reward
        
        v7_scores.append(v7_r)
        v8_scores.append(v8_r)
        v7_times.append(v7_t)
        v8_times.append(v8_t)
        
        speedup = v7_t / v8_t if v8_t > 0 else 0
        print(f"Ep {ep+1}: V7=${v7_r:.0f} ({v7_t:.3f}s)  V8=${v8_r:.0f} ({v8_t:.3f}s)  speed={speedup:.2f}x")
    
    avg_v7 = sum(v7_scores) / len(v7_scores)
    avg_v8 = sum(v8_scores) / len(v8_scores)
    avg_t7 = sum(v7_times) / len(v7_times)
    avg_t8 = sum(v8_times) / len(v8_times)
    
    print(f"\n--- Summary ---")
    print(f"V7 avg score: ${avg_v7:.0f}, avg time: {avg_t7:.3f}s")
    print(f"V8 avg score: ${avg_v8:.0f}, avg time: {avg_t8:.3f}s")
    print(f"Speedup: {avg_t7/avg_t8:.2f}x")
    print(f"Score diff: {avg_v8 - avg_v7:+.0f}")
    print(f"V7 wins: {sum(1 for a,b in zip(v7_scores, v8_scores) if a >= b)}/{n}")
    print(f"V8 wins: {sum(1 for a,b in zip(v7_scores, v8_scores) if b > a)}/{n}")

if __name__ == "__main__":
    compare(10)
