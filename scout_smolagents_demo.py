"""
Scout's smolagents CodeAgent Demo for DynastyDroid
Uses MiniMax M2.7 to solve a fantasy football task
"""

from smolagents import CodeAgent
from smolagents.models import LiteLLMModel

# Initialize MiniMax M2.7 model via LiteLLM
model = LiteLLMModel(
    model_id='minimax/MiniMax-M2.7',
    api_key='sk-cp-RRpXJ4C_F_lMU3SHtpr7q9ZQ_9A13OhXAbsDEFt1yR8hMyZ-8IK-eKr0JcugGR3u44Ch6I1S7K0s7L3i7PADtn5R0RmCifQbaupGDtM_9NAOAADfS3UxF1M'
)

# Create CodeAgent
agent = CodeAgent(
    model=model,
    tools=[]  # No tools needed for this simple task
)

# Task: Write a Python function that calculates total team value
task = """Write a Python function that takes a list of fantasy football player values and calculates the total team value. Then test it with 5 sample players: [8500, 6200, 4100, 2800, 1500]."""

print(f"Task: {task}\n")
print("=" * 60)
print("CodeAgent executing...\n")

# Run the agent
result = agent.run(task)

print("\n" + "=" * 60)
print(f"Final Result: {result}")
