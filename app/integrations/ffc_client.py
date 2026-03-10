"""
FantasyFootballCalculator API client for ADP data.

API Documentation: https://fantasyfootballcalculator.com/api
Note: This is a public API, no authentication required.
"""
import aiohttp
import logging
from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class FantasyFootballCalculatorClient:
    """Client for FantasyFootballCalculator ADP API."""
    
    BASE_URL = "https://fantasyfootballcalculator.com/api/v1"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = False
        
    async def __aenter__(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self._session:
            await self._session.close()
    
    async def get_adp(
        self, 
        year: int = 2025,
        scoring: str = "ppr",
        teams: int = 12,
        position: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ADP data from FantasyFootballCalculator.
        
        Args:
            year: Draft year (e.g., 2025)
            scoring: Scoring format ('ppr', 'half', 'standard')
            teams: Number of teams in league (8, 10, 12, 14)
            position: Filter by position ('QB', 'RB', 'WR', 'TE')
            
        Returns:
            List of player ADP data
        """
        endpoint = f"{self.BASE_URL}/adp/{scoring}"
        params = {
            "year": year,
            "teams": teams
        }
        
        if position:
            params["position"] = position
        
        try:
            async with self._session.get(endpoint, params=params) as response:
                if response.status != 200:
                    logger.error(f"FFC API error: {response.status} - {await response.text()}")
                    return []
                
                data = await response.json()
                
                # FFC API returns ADP data in 'players' field
                players = data.get("players", [])
                logger.info(f"Retrieved {len(players)} players from FFC API")
                return players
                
        except Exception as e:
            logger.error(f"Error fetching FFC ADP data: {e}")
            return []
    
    async def get_all_positions_adp(
        self,
        year: int = 2025,
        scoring: str = "ppr",
        teams: int = 12
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get ADP data for all positions.
        
        Returns dict with position as key and list of players as value.
        """
        positions = ["QB", "RB", "WR", "TE"]
        all_players = {}
        
        for position in positions:
            players = await self.get_adp(year, scoring, teams, position)
            all_players[position] = players
            # Rate limiting: be nice to the API
            await asyncio.sleep(0.5)
        
        return all_players
    
    async def health_check(self) -> bool:
        """Check if FFC API is accessible."""
        try:
            async with self._session.get(f"{self.BASE_URL}/adp/ppr", params={"year": 2025, "teams": 12}) as response:
                return response.status == 200
        except Exception:
            return False
    
    def normalize_player_data(self, ffc_player: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize FFC player data to match our schema.
        
        FFC API returns fields like:
        {
            "player_id": "12345",
            "name": "Christian McCaffrey",
            "position": "RB",
            "team": "SF",
            "adp": 1.2,
            "high": 1,
            "low": 3,
            "stdev": 0.5,
            "bye": 7
        }
        """
        normalized = {
            "ffc_id": ffc_player.get("player_id"),
            "name": ffc_player.get("name", ""),
            "position": ffc_player.get("position", ""),
            "team": ffc_player.get("team", ""),
            "adp": ffc_player.get("adp"),
            "adp_high": ffc_player.get("high"),
            "adp_low": ffc_player.get("low"),
            "adp_stdev": ffc_player.get("stdev"),
            "bye_week": ffc_player.get("bye"),
        }
        
        # Extract first and last name
        name_parts = normalized["name"].split()
        if len(name_parts) >= 2:
            normalized["first_name"] = name_parts[0]
            normalized["last_name"] = " ".join(name_parts[1:])
        else:
            normalized["first_name"] = normalized["name"]
            normalized["last_name"] = ""
        
        return normalized


# Singleton instance for easy access
_ffc_client = None

async def get_ffc_client() -> FantasyFootballCalculatorClient:
    """Get or create FFC client instance."""
    global _ffc_client
    if _ffc_client is None:
        _ffc_client = FantasyFootballCalculatorClient()
        await _ffc_client.__aenter__()
    return _ffc_client