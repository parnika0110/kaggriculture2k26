import sys, os, time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission

def time_agent(num_episodes=3):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    
    # Warm up
    env.reset()
    env.run([submission.agent, "starter"])
    
    # Time N full episodes
    times = []
    for ep in range(num_episodes):
        env.reset()
        start = time.perf_counter()
        env.run([submission.agent, "starter"])
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        res = [s.reward for s in env.steps[-1]]
        print(f"Episode {ep+1}: ${res[0]:.0f} vs ${res[1]:.0f} ({elapsed:.3f}s)")
    
    avg = sum(times) / len(times)
    # Total agent call time: 720 steps per episode
    per_call_us = (avg / 720) * 1_000_000
    print(f"\nAverage episode: {avg:.3f}s")
    print(f"Average per agent() call: {per_call_us:.1f}µs")
    print(f"Original baseline was ~0.5-2.5ms per call")
    return avg

if __name__ == "__main__":
    print("=== V8 Optimized Timing Benchmark ===\n")
    time_agent(3)
