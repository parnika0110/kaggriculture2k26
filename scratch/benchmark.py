import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kaggle_environments import make
import submission

def run_test(num_episodes=5):
    env = make("kaggriculture", configuration={"episodeSteps": 720})
    sub_wins = 0
    sub_scores = []
    starter_scores = []
    
    for ep in range(num_episodes):
        env.reset()
        env.run([submission.agent, "starter"])
        res = [s.reward for s in env.steps[-1]]
        sub_scores.append(res[0])
        starter_scores.append(res[1])
        if res[0] > res[1]:
            sub_wins += 1
        print(f"Episode {ep+1}: Agent=${res[0]:.0f} vs Starter=${res[1]:.0f}")
        
    avg_sub = sum(sub_scores) / len(sub_scores)
    avg_starter = sum(starter_scores) / len(starter_scores)
    print(f"\n--- Benchmark Results ---")
    print(f"Agent Win Rate: {sub_wins}/{num_episodes} ({sub_wins/num_episodes*100:.1f}%)")
    print(f"Average Agent Score: ${avg_sub:.2f}")
    print(f"Average Starter Score: ${avg_starter:.2f}")

if __name__ == "__main__":
    run_test(5)
