import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission

def run_self_play(num_episodes=3):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    for ep in range(num_episodes):
        env.reset()
        env.run([submission.agent, submission.agent])
        res = [s.reward for s in env.steps[-1]]
        print(f"Self-Play Episode {ep+1}: P0=${res[0]:.0f} vs P1=${res[1]:.0f}")

def run_vs_random(num_episodes=3):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    for ep in range(num_episodes):
        env.reset()
        env.run([submission.agent, "random"])
        res = [s.reward for s in env.steps[-1]]
        print(f"Vs Random Episode {ep+1}: Agent=${res[0]:.0f} vs Random=${res[1]:.0f}")

if __name__ == "__main__":
    print("--- Running Self-Play Test ---")
    run_self_play(3)
    print("\n--- Running Vs Random Test ---")
    run_vs_random(3)
