"""
Multi-Year Fantasy Data Module

Loads and manages fantasy data across multiple years (2022-2025).
Creates training generalization by exposing RL to different year patterns.

Data structure per year:
{
  "year": YYYY,
  "players": {
    "player_name": {
      "fpts_ppr": float,  # Total PPR fantasy points
      "games": int,         # Games played
      "ppg": float,         # Points per game
      "position": str,      # QB/RB/WR/TE
      "pos_rank": int,      # Position ranking
      "age": int,          # Age that season
    }
  }
}

Usage:
    multi_year = MultiYearData()
    year = multi_year.get_random_year()
    pts = multi_year.get_points(player_name, year=year)
"""

import json
import random
from typing import Dict, Optional, List


class MultiYearData:
    """Manages multi-year fantasy data for training"""
    
    YEARS = ['2022', '2023', '2024', '2025']
    
    def __init__(self, data_dir: str = '.'):
        self.data_dir = data_dir
        self.data: Dict[str, Dict] = {}
        self._load_data()
    
    def _load_data(self):
        """Load all available year data"""
        for year in self.YEARS:
            filename = f"{self.data_dir}/fantasy_points_{year}.json"
            try:
                with open(filename, 'r') as f:
                    self.data[year] = json.load(f)
                print(f"Loaded {year}: {len(self.data[year])} players")
            except FileNotFoundError:
                print(f"No data for {year}")
    
    def get_random_year(self) -> str:
        """Get random year for training"""
        return random.choice(self.YEARS)
    
    def get_available_years(self) -> List[str]:
        """Return list of years with data"""
        return list(self.data.keys())
    
    def get_player_data(self, name: str, year: str = None) -> Optional[Dict]:
        """Get single player data for a year"""
        if year is None:
            year = self.get_random_year()
        
        if year not in self.data:
            return None
        
        # Search by name
        for player in self.data[year]:
            if player.get('name') == name:
                return player
        return None
    
    def get_points(self, name: str, year: str = None) -> float:
        """Get fantasy points for player in year"""
        player = self.get_player_data(name, year)
        if player:
            return player.get('fpts_ppr', 0)
        return 0
    
    def get_ppg(self, name: str, year: str = None) -> float:
        """Get points per game"""
        player = self.get_player_data(name, year)
        if player and player.get('games', 0) > 0:
            return player.get('fpts_ppr', 0) / player.get('games', 1)
        return 0
    
    def effective_points(self, name: str, year: str = None) -> float:
        """
        Calculate effective points with waiver floor.
        
        If player played < 8 games, project to full season.
        Otherwise return actual points.
        """
        player = self.get_player_data(name, year)
        
        if not player:
            return 0
        
        games = player.get('games', 0)
        fpts = player.get('fpts_ppr', 0)
        
        if games < 8 and games > 0:
            # Project to full season
            return (fpts / games) * 17
        elif games == 0:
            return 0  # Didn't play
        
        return fpts


# Create example multi-year structure for 2025 (expandable)
def create_multi_year_template():
    """Create empty multi-year structure"""
    
    # Load existing 2025 data
    with open('fantasy_points_2025.json', 'r') as f:
        data_2025 = json.load(f)
    
    # Create template
    template = {
        "2025": {
            "year": 2025,
            "source": "fantasypros",
            "players": data_2025
        },
        "2024": {
            "year": 2024,
            "source": "needs_data",
            "players": []
        },
        "2023": {
            "year": 2023,
            "source": "needs_data", 
            "players": []
        },
        "2022": {
            "year": 2022,
            "source": "needs_data",
            "players": []
        }
    }
    
    return template


if __name__ == '__main__':
    print("="*60)
    print("MULTI-YEAR DATA MANAGER")
    print("="*60)
    
    # Try loading
    multi = MultiYearData()
    
    print(f"\nAvailable years: {multi.get_available_years()}")
    
    # Test 2025
    if '2025' in multi.data:
        pts = multi.get_points('Josh Allen', '2025')
        print(f"\nJosh Allen 2025: {pts} pts")
        
        eff = multi.effective_points('Josh Allen', '2025')
        print(f"Josh Allen effective: {eff} pts")
    
    # Create template for future years
    template = create_multi_year_template()
    
    with open('multi_year_template.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print("\nCreated multi_year_template.json")
    print("Next: Add 2022-2024 data from FantasyPros API")
