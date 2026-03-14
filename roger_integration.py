"""
Roger Integration for DynastyDroid Draft

Connects Roger (LLM) to the DraftEnv for intelligent picks.
"""

import json
import re
from typing import Dict, Optional, List
from draft_env import DraftEnv

# Prompt template for Roger
ROGER_PROMPT_TEMPLATE = """You are Roger, a fantasy football draft bot. You're in a 12-team Superflex snake draft.

=== YOUR ROSTER ===
{roster}

=== POSITION NEEDS ===
{needs}

=== AVAILABLE TOP 20 PLAYERS ===
{available_players}

=== DRAFT STATUS ===
- Round: {round}
- Pick: {pick}
- Your slot: {team_id}

Choose the best player. Return ONLY the player name from the list."""


def create_roger_prompt(state: Dict) -> str:
    """Create prompt for Roger based on current state"""
    
    # Format roster
    roster = state.get('roster', [])
    roster_str = ", ".join(roster) if roster else "Empty"
    
    # Format needs
    needs = state.get('roster_needs', {})
    needs_str = ", ".join([f"{k}: {v}" for k, v in needs.items()])
    
    # Format available players
    available = state.get('available_top20', [])
    players_str = "\n".join([
        f"{i}. {p['name']:<25} {p['position']:<3} ADP:{p['adp']:>4.0f} FPTS:{p['fpts']:>5.1f}"
        for i, p in enumerate(available)
    ])
    
    return ROGER_PROMPT_TEMPLATE.format(
        roster=roster_str,
        needs=needs_str,
        available_players=players_str,
        round=state['round'],
        pick=state['pick'],
        team_id=state['team_id']
    )


def parse_roger_response(response: str, available: List[Dict]) -> int:
    """
    Parse Roger's response to get the player index.
    
    Args:
        response: Roger's text response
        available: List of available players
        
    Returns:
        Index of selected player (0-19)
    """
    # Try to extract player name from response
    response = response.strip()
    
    # First, try to find exact match in available players
    for i, player in enumerate(available):
        if player['name'].lower() in response.lower():
            return i
    
    # Try to find partial match
    for i, player in enumerate(available):
        name_parts = player['name'].lower().split()
        for part in name_parts:
            if len(part) > 3 and part in response.lower():
                return i
    
    # Try to extract a number from response
    numbers = re.findall(r'\d+', response)
    if numbers:
        idx = int(numbers[0])
        if 0 <= idx < len(available):
            return idx
    
    # Default to first player (ADP) if can't parse
    return 0


class RogerDraftEnv(DraftEnv):
    """DraftEnv with Roger integration"""
    
    def __init__(self, roger_llm_fn=None, players_file: str = None):
        """
        Initialize with Roger LLM function.
        
        Args:
            roger_llm_fn: Function that takes prompt, returns response
        """
        super().__init__(players_file)
        self.roger_llm_fn = roger_llm_fn
    
    def roger_pick(self, state: Dict) -> int:
        """
        Get Roger's pick using the LLM.
        
        Args:
            state: Current draft state
            
        Returns:
            Index of selected player (0-19)
        """
        if self.roger_llm_fn is None:
            # No LLM, use ADP fallback
            return 0
        
        # Create prompt
        prompt = create_roger_prompt(state)
        
        # Get response from LLM
        response = self.roger_llm_fn(prompt)
        
        # Parse response
        available = state['available_top20']
        return parse_roger_response(response, available)
    
    def run_episode_with_roger(self, roger_model: str = None) -> Dict:
        """
        Run a full draft episode with Roger making picks.
        
        Args:
            roger_model: Model to use for Roger (optional)
            
        Returns:
            Episode results
        """
        state = self.reset()
        
        while True:
            team = self.teams[self.current_team_idx]
            
            if team.strategy == "ROGER":
                # Get Roger's pick
                action = self.roger_pick(state)
            else:
                # Bot pick
                action = self.bot_pick()
            
            state, reward, done, info = self.step(action)
            
            if done:
                break
        
        return {
            'roger_slot': self.roger_slot,
            'reward': reward,
            'roster': info.get('final_roster', []),
            'draft_log': self.draft_log,
            'total_points': reward + 2500  # Add back league avg
        }


# Mock LLM for testing
def mock_roger_llm(prompt: str) -> str:
    """Mock LLM that picks by ADP (lowest = best)"""
    # Parse ADP from prompt lines
    best_line = None
    best_adp = float('inf')
    
    for line in prompt.split('\n'):
        if 'ADP:' in line:
            try:
                # Extract ADP value
                adp_str = line.split('ADP:')[1].split()[0]
                adp = float(adp_str)
                if adp < best_adp:
                    best_adp = adp
                    best_line = line.strip()
            except:
                pass
    
    return best_line if best_line else "0"


# Real MiniMax LLM
def minimax_roger_llm(prompt: str, model: str = "MiniMax-M2.5") -> str:
    """Real Roger LLM using MiniMax API"""
    import subprocess
    import json
    
    API_KEY = "sk-cp-FqLcyjipNnLkczzHryLDaDjY06jPVUm2j88vG1KXIzLxPyiJIh3UaFkPz9KF8OGEAAIzns9rQLxYMIWZBPmGvDUmCyl-28rKfNGz_qffOlca87FJP3c"
    
    # Create a script that calls MiniMax
    script = f'''
import requests
import json

url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
headers = {{
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}}

data = {{
    "model": "MiniMax-M2.5",
    "messages": [
        {{"role": "system", "content": "You are Roger, a fantasy football draft expert. Analyze the draft situation and pick the best available player. Return ONLY the player name and position from the list provided."}},
        {{"role": "user", "content": {repr(prompt[:2000])}}}
    ],
    "temperature": 0.7,
    "max_tokens": 100
}}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result["choices"][0]["message"]["content"])
'''
    
    try:
        result = subprocess.run(
            ['python3', '-c', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error: {result.stderr}")
            return mock_roger_llm(prompt)  # Fallback
    except Exception as e:
        print(f"Exception: {e}")
        return mock_roger_llm(prompt)  # Fallback


# Test
if __name__ == '__main__':
    # Use real MiniMax LLM
    print("=== ROGER INTEGRATION TEST WITH MINIMAX ===\n")
    print("Using MiniMax-M2.5 for picks...\n")
    
    env = RogerDraftEnv(roger_llm_fn=minimax_roger_llm)
    
    # Run one episode
    result = env.run_episode_with_roger()
    
    print(f"Roger Slot: {result['roger_slot']}")
    print(f"Reward: {result['reward']:.1f}")
    print(f"Total Points: {result['total_points']:.1f}")
    
    # Count positions
    roster = result['roster']
    pos_counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for name in roster:
        for p in env.player_pool:
            if p.name == name:
                pos_counts[p.position] = pos_counts.get(p.position, 0) + 1
                break
    print(f"Roster: {pos_counts}")
    
    # Show Roger's picks
    roger_picks = [p for p in result['draft_log'] if p['team'] == result['roger_slot']]
    print(f"\nRoger's picks (first 10):")
    for pick in roger_picks[:10]:
        print(f"  Pick {pick['pick']}: {pick['player']} ({pick['position']})")
