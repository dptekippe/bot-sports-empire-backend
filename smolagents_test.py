"""
Test script for smolagents CodeAgent with MiniMax model via LiteLLM
"""
from smolagents import CodeAgent
from smolagents.models import LiteLLMModel

def main():
    api_key = "sk-cp-RRpXJ4C_F_lMU3SHtpr7q9ZQ_9A13OhXAbsDEFt1yR8hMyZ-8IK-eKr0JcugGR3u44Ch6I1S7K0s7L3i7PADtn5R0RmCifQbaupGDtM_9NAOAADfS3UxF1M"
    
    # Try without base_url - LiteLLM should auto-detect
    model = LiteLLMModel(
        model_id="minimax/MiniMax-M2.7",
        api_key=api_key
    )
    print("Using MiniMax M2.7 via LiteLLM (no base_url)")

    agent = CodeAgent(model=model, tools=[])

    task = "What is 2+2? Answer with just the number."
    print(f"Running agent with task: '{task}'")

    result = agent.run(task)

    print(f"\nResult: {result}")
    return result

if __name__ == "__main__":
    main()
