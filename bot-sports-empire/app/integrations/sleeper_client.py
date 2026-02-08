"""
Sleeper API Client for Bot Sports Empire.

Clean abstraction layer for Sleeper Fantasy Football API.
All HTTP calls and rate limiting are encapsulated here.
"""
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class SleeperPlayerRaw:
    """Raw player data from Sleeper API - minimal typing for initial implementation"""
    player_id: str
    data: Dict[str, Any]


class SleeperClient:
    """Clean, minimal client for Sleeper API with built-in rate limiting and caching."""
    
    BASE_URL = "https://api.sleeper.app/v1"
    
    def __init__(self, cache_dir: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize Sleeper client.
        
        Args:
            cache_dir: Directory to cache API responses (default: ~/.cache/bot-sports-empire/sleeper)
            session: Optional aiohttp session for connection pooling
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "bot-sports-empire" / "sleeper"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._session = session
        self._own_session = session is None
        
        # Rate limiting: Sleeper recommends staying under ~1000 calls/minute
        self._last_request_time = 0
        self._min_request_interval = 0.06  # 60ms between requests = ~1000/minute
        
        # Cache TTLs (in seconds)
        self._players_cache_ttl = 24 * 60 * 60  # 24 hours for full player dump
        self._player_cache_ttl = 60 * 60  # 1 hour for individual players
        
    async def __aenter__(self):
        if self._own_session:
            self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self._session:
            await self._session.close()
    
    def _get_cache_path(self, endpoint: str) -> Path:
        """Get cache file path for an endpoint."""
        # Create a safe filename from endpoint
        cache_key = hashlib.md5(endpoint.encode()).hexdigest()
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_path: Path, ttl: int) -> bool:
        """Check if cache is still valid."""
        if not cache_path.exists():
            return False
        
        cache_age = time.time() - cache_path.stat().st_mtime
        return cache_age < ttl
    
    def _read_cache(self, cache_path: Path) -> Optional[Dict[str, Any]]:
        """Read data from cache file."""
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    
    def _write_cache(self, cache_path: Path, data: Dict[str, Any]):
        """Write data to cache file."""
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    async def _make_request(self, endpoint: str, use_cache: bool = True, cache_ttl: int = 3600) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request to Sleeper API with rate limiting and caching.
        
        Args:
            endpoint: API endpoint (e.g., "/players/nfl")
            use_cache: Whether to use cached responses
            cache_ttl: Cache TTL in seconds
            
        Returns:
            JSON response as dict, or None if request failed
        """
        url = f"{self.BASE_URL}{endpoint}"
        cache_path = self._get_cache_path(endpoint)
        
        # Check cache first
        if use_cache and self._is_cache_valid(cache_path, cache_ttl):
            logger.debug(f"Using cached response for {endpoint}")
            return self._read_cache(cache_path)
        
        # Rate limit before making request
        await self._rate_limit()
        
        try:
            logger.info(f"Fetching {url}")
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache successful response
                    if use_cache:
                        self._write_cache(cache_path, data)
                    
                    return data
                else:
                    logger.error(f"Sleeper API error {response.status} for {endpoint}")
                    return None
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {endpoint}: {e}")
            return None
    
    async def get_all_players(self, use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get all NFL players from Sleeper API.
        
        This is a ~5MB payload, so we cache aggressively (24 hours).
        Sleeper recommends not calling this more than once per day.
        
        Returns:
            Dictionary mapping player_id -> player data
        """
        endpoint = "/players/nfl"
        data = await self._make_request(endpoint, use_cache=use_cache, cache_ttl=self._players_cache_ttl)
        
        if data is None:
            logger.warning("Failed to fetch all players, returning empty dict")
            return {}
        
        # Sleeper returns a dict where keys are player IDs
        return data
    
    async def get_player(self, player_id: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get single player by ID.
        
        Note: Sleeper doesn't have a direct single-player endpoint,
        but we can extract from the full player dump.
        
        Args:
            player_id: Sleeper player ID
            use_cache: Whether to use cached data
            
        Returns:
            Player data dict, or None if not found
        """
        all_players = await self.get_all_players(use_cache=use_cache)
        return all_players.get(player_id)
    
    async def get_players_batch(self, player_ids: List[str], use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple players by ID.
        
        Args:
            player_ids: List of Sleeper player IDs
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary of player_id -> player data for found players
        """
        all_players = await self.get_all_players(use_cache=use_cache)
        return {pid: all_players[pid] for pid in player_ids if pid in all_players}
    
    async def get_trending_players(self, type: str = "add", lookback_hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """
        Get trending players (most added/dropped).
        
        Args:
            type: "add" or "drop"
            lookback_hours: How many hours to look back (max 168 = 7 days)
            
        Returns:
            List of trending player data, or None if request failed
        """
        endpoint = f"/players/nfl/trending/{type}?lookback_hours={lookback_hours}"
        return await self._make_request(endpoint, cache_ttl=3600)  # 1 hour cache
    
    async def get_player_stats(self, season: int, week: int, player_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get player stats for a specific season and week.
        
        Args:
            season: NFL season year (e.g., 2025)
            week: Week number (1-18 for regular season)
            player_id: Optional specific player ID
            
        Returns:
            Stats data, or None if request failed
        """
        if player_id:
            endpoint = f"/stats/nfl/player/{player_id}/{season}/{week}"
        else:
            endpoint = f"/stats/nfl/season/{season}/week/{week}"
        
        return await self._make_request(endpoint, cache_ttl=3600)  # 1 hour cache
    
    async def get_nfl_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current NFL state (season, week, etc.).
        
        Returns:
            NFL state data, or None if request failed
        """
        endpoint = "/state/nfl"
        return await self._make_request(endpoint, cache_ttl=300)  # 5 minute cache
    
    async def health_check(self) -> bool:
        """
        Check if Sleeper API is accessible.
        
        Returns:
            True if API is responsive, False otherwise
        """
        try:
            data = await self.get_nfl_state()
            return data is not None and "season" in data
        except Exception:
            return False


# Convenience function for synchronous contexts
def get_sleeper_client() -> SleeperClient:
    """Get a Sleeper client instance for synchronous use."""
    return SleeperClient()


async def test_client():
    """Test the Sleeper client."""
    import asyncio
    
    async with SleeperClient() as client:
        # Test health check
        healthy = await client.health_check()
        print(f"Sleeper API healthy: {healthy}")
        
        if healthy:
            # Get NFL state
            state = await client.get_nfl_state()
            if state:
                print(f"Current season: {state.get('season')}, week: {state.get('week')}")
            
            # Get all players (cached)
            players = await client.get_all_players()
            print(f"Total players: {len(players)}")
            
            # Get a sample player
            if players:
                sample_id = list(players.keys())[0]
                player = players[sample_id]
                print(f"Sample player: {player.get('first_name')} {player.get('last_name')} ({player.get('position')})")


if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_client())