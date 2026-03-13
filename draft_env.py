"""
Draft Environment for DynastyDroid RL Training

Supports multiple bot strategies for diverse draft simulation.
"""

import json
import random
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from rl_reward import get_fpts, load_top164, check_roster_legality

# Constants
NUM_TEAMS = 12
ROSTER_SIZE = 20
STARTERS = {
    'QB': 1,
    'RB': 2,
    'WR': 2,
    'TE': 1,
    'FLEX': 3,  # RB/WR/TE
    'SUPERFLEX': 1,  # QB/RB/WR/TE
}


@dataclass
class Player:
    name: str
    position: str
    team: str
    adp: float
    fpts: float = 0.0
    
    def __post_init__(self):
        if self.fpts == 0.0:
            self.fpts = get_fpts(self.name, int(self.adp))


@dataclass
class Team:
    team_id: int
    roster: List[Player] = field(default_factory=list)
    strategy: str = "ADP"
    
    def needs(self) -> Dict[str, int]:
        """Return position needs for starters"""
        counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
        for p in self.roster:
            if p.position in counts:
                counts[p.position] += 1
        return counts
    
    def starter_count(self) -> int:
        return sum(1 for p in self.roster if p.position in ['QB', 'RB', 'WR', 'TE'])


class DraftEnv:
    """Fantasy Football Draft Environment"""
    
    def __init__(self, players_file: str = None):
        """Initialize draft environment"""
        # Load players
        if players_file:
            with open(players_file, 'r') as f:
                self.all_players = json.load(f)
        else:
            # Try default locations
            import os
            for path in [
                'fantasy_points_2025.json',
                os.path.expanduser('~/.openclaw/workspace/fantasy_points_2025.json'),
                '/tmp/fantasy_points_2025.json'
            ]:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self.all_players = json.load(f)
                    break
        
        # Build player pool with ADP
        self.player_pool = self._build_player_pool()
        
        # Bot strategies
        self.strategies = {
            'ADP': self._strategy_adp,
            'ZeroRB': self._strategy_zerorb,
            'HeroRB': self._strategy_herorb,
            'LateQB': self._strategy_lateqb,
            'EliteTE': self._strategy_elitete,
            'Contrarian': self._strategy_contrarian,
            'SafeFloor': self._strategy_safefloor,
            'Boulevard': self._strategy_boulevard,
        }
    
    def _build_player_pool(self) -> List[Player]:
        """Build player pool with ADP values"""
        players = []
        
        # Load ADP data from correct file
        adp_lookup = {}
        try:
            with open('/Users/danieltekippe/.openclaw/workspace/adp_2025_filtered.json', 'r') as f:
                adp_data = json.load(f)
            adp_lookup = {p['name']: p['adp'] for p in adp_data}
            print(f"Loaded {len(adp_lookup)} players with ADP")
        except Exception as e:
            print(f"Could not load ADP file: {e}")
            return players
        
        # First add all players with valid ADP
        adp_players = []
        for adp_name, adp in adp_lookup.items():
            # Try to find matching player in fantasy_points
            fpts = 0
            pos = 'WR'  # default
            team = ''   # default
            
            for fp in self.all_players:
                if fp['name'] == adp_name:
                    fpts = fp.get('fpts_ppr', 0)
                    pos = fp.get('position', 'WR')
                    team = fp.get('team', '')
                    break
            
            adp_players.append(Player(
                name=adp_name,
                position=pos,
                team=team,
                adp=float(adp),
                fpts=float(fpts)
            ))
        
        players.extend(adp_players)
        
        # Fill remaining spots from fantasy_points (players not in ADP)
        fp_names_used = set(adp_lookup.keys())
        for fp in self.all_players:
            if fp['name'] not in fp_names_used:
                # Add with high ADP (last)
                players.append(Player(
                    name=fp['name'],
                    position=fp.get('position', 'WR'),
                    team=fp.get('team', ''),
                    adp=float(len(adp_lookup) + len(players) - len(adp_players) + 1),
                    fpts=float(fp.get('fpts_ppr', 0))
                ))
        
        # Sort by ADP
        players.sort(key=lambda x: x.adp)
        return players
    
    def reset(self, roger_slot: int = None, strategy_mix: List[str] = None) -> Dict:
        """Reset environment for new draft"""
        # Assign Roger to random slot if not specified
        if roger_slot is None:
            roger_slot = random.randint(1, NUM_TEAMS)
        
        # Default strategy mix
        if strategy_mix is None:
            strategy_mix = list(self.strategies.keys())
        
        # Initialize teams
        self.teams = []
        for i in range(1, NUM_TEAMS + 1):
            strategy = strategy_mix[i % len(strategy_mix)]
            if i == roger_slot:
                strategy = "ROGER"
            self.teams.append(Team(team_id=i, strategy=strategy))
        
        # Copy available players
        self.available = self.player_pool.copy()
        
        # Draft state
        self.current_pick = 1
        self.current_team_idx = 0
        self.roger_slot = roger_slot
        self.draft_log = []
        self.round = 1
        
        return self._get_state()
    
    def step(self, action: int) -> Tuple[Dict, float, bool, Dict]:
        """Execute one pick"""
        # Get current team
        team = self.teams[self.current_team_idx]
        
        # Bounds check
        if action < 0:
            action = 0
        
        # Apply pick (action is index in available[:20])
        available_top20 = self.available[:20]
        if action >= len(available_top20) or action >= len(self.available):
            action = min(0, len(self.available) - 1)
        
        player = self.available[action]
        
        # Add to roster
        team.roster.append(player)
        
        # Remove from available
        self.available.remove(player)
        
        # Log pick
        self.draft_log.append({
            'pick': self.current_pick,
            'team': team.team_id,
            'strategy': team.strategy,
            'player': player.name,
            'position': player.position,
            'adp': player.adp,
            'fpts': player.fpts
        })
        
        # Advance draft
        self._advance_draft()
        
        # Calculate reward (only at end)
        done = len(self.teams[self.roger_slot - 1].roster) >= ROSTER_SIZE
        
        if done:
            reward = self._calculate_reward(self.roger_slot)
            info = {'final_roster': [p.name for p in self.teams[self.roger_slot - 1].roster]}
        else:
            reward = 0
            info = {}
        
        return self._get_state(), reward, done, info
    
    def bot_pick(self) -> int:
        """Execute bot pick, return action index"""
        team = self.teams[self.current_team_idx]
        
        if team.strategy == "ROGER":
            return 0  # Placeholder - Roger will choose
        
        # Get strategy function
        strategy_fn = self.strategies.get(team.strategy, self._strategy_adp)
        
        # Get action from strategy
        action = strategy_fn(team, self.available[:50], self.round)
        
        return action
    
    def _advance_draft(self):
        """Advance to next pick (snake draft)"""
        self.current_pick += 1
        
        # Snake draft - reverse order every other round
        self.round = (self.current_pick - 1) // NUM_TEAMS + 1
        
        # Reverse at START of even rounds (before pick)
        if self.round > 1 and self.round % 2 == 0:
            self.teams = self.teams[::-1]
        
        # Advance to next team
        self.current_team_idx = (self.current_team_idx + 1) % NUM_TEAMS
    
    def _get_state(self) -> Dict:
        """Get current state for Roger"""
        team = self.teams[self.current_team_idx]
        
        return {
            'pick': self.current_pick,
            'round': self.round,
            'team_id': team.team_id,
            'roster': [p.name for p in team.roster],
            'roster_needs': team.needs(),
            'available_top20': [
                {
                    'name': p.name,
                    'position': p.position,
                    'team': p.team,
                    'adp': p.adp,
                    'fpts': p.fpts
                }
                for p in self.available[:20]
            ]
        }
    
    def _calculate_reward(self, roger_slot: int) -> float:
        """Calculate reward for Roger's team"""
        team = self.teams[roger_slot - 1]
        
        # Sum of fantasy points
        total_pts = sum(p.fpts for p in team.roster)
        
        # League average (estimated)
        league_avg = 2500
        
        # Roster legality penalty
        penalty = 0
        needs = team.needs()
        if needs['QB'] < 1: penalty -= 50
        if needs['RB'] < 2: penalty -= 50
        if needs['WR'] < 2: penalty -= 50
        if needs['TE'] < 1: penalty -= 50
        
        return total_pts + penalty - league_avg
    
    # ========== STRATEGIES ==========
    
    def _strategy_adp(self, team: Team, available: List[Player], round_num: int) -> int:
        """Take best available by ADP"""
        return 0  # First player = lowest ADP = best
    
    def _strategy_zerorb(self, team: Team, available: List[Player], round_num: int) -> int:
        """Zero RB - skip RB in early rounds, load WR"""
        needs = team.needs()
        
        # Early rounds: avoid RB
        if round_num <= 6:
            # Prefer WR, TE, QB over RB
            for i, p in enumerate(available):
                if p.position != 'RB':
                    return i
        
        # Mid/late: fill RB needs
        if needs['RB'] < 2 and round_num > 6:
            for i, p in enumerate(available):
                if p.position == 'RB':
                    return i
        
        # Default: best available
        return 0
    
    def _strategy_herorb(self, team: Team, available: List[Player], round_num: int) -> int:
        """Hero RB - take one elite RB early, then WR"""
        needs = team.needs()
        
        # Round 1-2: take elite RB
        if round_num <= 2 and needs['RB'] == 0:
            for i, p in enumerate(available):
                if p.position == 'RB' and p.adp <= 20:
                    return i
        
        # Rounds 3+: fill WR
        for i, p in enumerate(available):
            if p.position == 'WR':
                return i
        
        return 0
    
    def _strategy_lateqb(self, team: Team, available: List[Player], round_num: int) -> int:
        """Late QB - wait until round 10+ for QB"""
        needs = team.needs()
        
        # Don't take QB early
        if round_num < 10:
            for i, p in enumerate(available):
                if p.position != 'QB':
                    return i
        
        # Round 10+: take QB if needed
        if needs['QB'] == 0:
            for i, p in enumerate(available):
                if p.position == 'QB':
                    return i
        
        return 0
    
    def _strategy_elitete(self, team: Team, available: List[Player], round_num: int) -> int:
        """Elite TE - grab top TE early (Kelce, McBride)"""
        needs = team.needs()
        
        # Rounds 2-5: take elite TE
        if 2 <= round_num <= 5 and needs['TE'] == 0:
            for i, p in enumerate(available):
                if p.position == 'TE' and p.fpts >= 100:
                    return i
        
        return 0
    
    def _strategy_contrarian(self, team: Team, available: List[Player], round_num: int) -> int:
        """Contrarian - fade popular players, take opposite"""
        # Invert ADP - take highest ADP (least popular) first
        available_sorted = sorted(available, key=lambda x: x.adp, reverse=True)
        
        # But still need to fill positions
        needs = team.needs()
        for p in available_sorted:
            if needs.get(p.position, 0) < STARTERS.get(p.position, 0):
                return available.index(p)
        
        return 0
    
    def _strategy_safefloor(self, team: Team, available: List[Player], round_num: int) -> int:
        """Safe Floor - prefer consistent players"""
        # Estimate floor by ratio of fpts to variance (simplified)
        # For now: prefer players with lower ADP variance (more proven)
        
        needs = team.needs()
        
        # Priority: fill needs with lowest-ADP (most proven) players
        for pos, needed in needs.items():
            if needed < STARTERS.get(pos, 0):
                for i, p in enumerate(available):
                    if p.position == pos:
                        return i
        
        return 0
    
    def _strategy_boulevard(self, team: Team, available: List[Player], round_num: int) -> int:
        """Boulevard - high upside late picks"""
        # Late rounds (15+): take high-variance players
        if round_num >= 15:
            # Prefer players with high fpts potential but high ADP (upside)
            available_sorted = sorted(available, key=lambda x: x.fpts, reverse=True)
            return available.index(available_sorted[0])
        
        # Early: still need to build foundation
        return 0


def run_episode(env: DraftEnv, roger_strategy_fn=None) -> Dict:
    """Run one draft episode"""
    state = env.reset()
    
    while True:
        team = env.teams[env.current_team_idx]
        
        if team.strategy == "ROGER":
            # Roger would choose here
            # For now, use ADP as fallback
            action = 0
        else:
            action = env.bot_pick()
        
        state, reward, done, info = env.step(action)
        
        if done:
            break
    
    return {
        'roger_slot': env.roger_slot,
        'reward': reward,
        'roster': info.get('final_roster', []),
        'draft_log': env.draft_log
    }


# Test
if __name__ == '__main__':
    env = DraftEnv()
    
    # Run test episode
    result = run_episode(env)
    
    print(f"=== TEST EPISODE ===")
    print(f"Roger Slot: {result['roger_slot']}")
    print(f"Reward: {result['reward']:.1f}")
    print(f"Roster Size: {len(result['roster'])}")
    print(f"\nFirst 10 picks:")
    for pick in result['draft_log'][:10]:
        print(f"  {pick['pick']}: {pick['team']} - {pick['player']} ({pick['position']})")
