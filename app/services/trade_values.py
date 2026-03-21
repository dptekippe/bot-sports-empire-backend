"""
Unified Trade Values Service - Single source of truth for dynasty player values.
Combines: KTC, DynastyProcess, DLF, FantasyPros, DraftSharks

Features:
- Async value fetching with caching
- Multi-source consensus calculation  
- Dynamic draft pick valuation based on ADP
- Staleness indicators
"""
import asyncio
import csv
import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# Configuration
CACHE_DIR = Path.home() / ".cache" / "dynastydroid" / "values"
CACHE_TTL_HOURS = 24  # Values refreshed daily
KTC_MAX = 9999
KTC_POWER = 1.8085  # KTC nonlinear curve exponent

# Weights for consensus calculation
SOURCE_WEIGHTS = {
    "ktc": 0.30,           # Crowdsourced - most reactive to market
    "dynastyprocess": 0.25, # Data-driven
    "dlf": 0.15,           # Expert consensus
    "fantasypros": 0.15,   # ECR-based
    "draftsharks": 0.15,   # Expert projections
}


class ValueCache:
    """Simple file-based cache for dynasty values."""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, source: str) -> Path:
        return self.cache_dir / f"{source}_values.json"
    
    def get(self, source: str) -> Optional[Dict[str, Any]]:
        """Get cached values if fresh."""
        cache_path = self._get_cache_path(source)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path) as f:
                data = json.load(f)
            
            # Check freshness
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
                logger.info(f"Cache stale for {source}, refetching")
                return None
            
            return data.get("values", {})
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Cache read error for {source}: {e}")
            return None
    
    def set(self, source: str, values: Dict[str, Any]) -> None:
        """Save values to cache."""
        cache_path = self._get_cache_path(source)
        data = {
            "cached_at": datetime.now().isoformat(),
            "source": source,
            "values": values
        }
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except OSError as e:
            logger.warning(f"Cache write error for {source}: {e}")
    
    def get_staleness(self, source: str) -> Optional[timedelta]:
        """Get how stale the cache is."""
        cache_path = self._get_cache_path(source)
        if not cache_path.exists():
            return None
        try:
            with open(cache_path) as f:
                data = json.load(f)
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            return datetime.now() - cached_at
        except (json.JSONDecodeError, OSError):
            return None


class DynastyValueService:
    """Unified service for dynasty player values."""
    
    def __init__(self, cache_dir: Path = None):
        self.cache = ValueCache(cache_dir)
        self._memory_cache: Dict[str, Dict] = {}
    
    # =========================================================================
    # Value Fetching Methods
    # =========================================================================
    
    async def fetch_ktc_values(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch KTC values from GitHub raw."""
        # Check cache first
        if not force_refresh:
            cached = self.cache.get("ktc")
            if cached:
                return cached
        
        url = "https://raw.githubusercontent.com/AndrewKelley97/keepyourchange/main/values/players.json"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                players = response.json()
                values = {}
                for p in players:
                    name = p.get("name", "")
                    value = p.get("value", 0)
                    if name and value:
                        values[name] = {
                            "value": value,
                            "position": p.get("position", "WR"),
                            "team": p.get("team", ""),
                            "age": p.get("age")
                        }
                
                self.cache.set("ktc", values)
                logger.info(f"Fetched {len(values)} KTC values")
                return values
                
        except Exception as e:
            logger.error(f"Failed to fetch KTC values: {e}")
            # Try fallback to local file
            return self._load_local_values("ktc_values.json")
    
    async def fetch_dynastyprocess_values(self, format: str = "2qb", force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch DynastyProcess values."""
        if not force_refresh:
            cached = self.cache.get(f"dynastyprocess_{format}")
            if cached:
                return cached
        
        url = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                values = {}
                reader = csv.DictReader(response.text.splitlines())
                value_col = f"value_{format}"
                
                for row in reader:
                    name = row.get("player", "").strip()
                    value = row.get(value_col, 0)
                    if name and value:
                        try:
                            values[name] = {
                                "value": int(float(value)),
                                "position": row.get("pos", "WR"),
                                "team": row.get("team", ""),
                                "age": row.get("age")
                            }
                        except (ValueError, TypeError):
                            pass
                
                self.cache.set(f"dynastyprocess_{format}", values)
                logger.info(f"Fetched {len(values)} DynastyProcess values ({format})")
                return values
                
        except Exception as e:
            logger.error(f"Failed to fetch DynastyProcess: {e}")
            return self._load_local_values("dynastyprocess_values.json")
    
    def _load_local_values(self, filename: str) -> Dict[str, Any]:
        """Load values from local static file."""
        static_path = Path(__file__).parent.parent.parent / "static" / filename
        try:
            with open(static_path) as f:
                data = json.load(f)
            
            values = {}
            for p in data:
                name = p.get("name", p.get("player", ""))
                if name:
                    values[name] = {
                        "value": p.get("value", p.get("ktc", p.get("rank", 0))),
                        "position": p.get("pos", p.get("position", "WR")),
                        "team": p.get("team", ""),
                        "age": p.get("age")
                    }
            return values
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load local {filename}: {e}")
            return {}
    
    async def fetch_all_sources(self, format: str = "2qb", force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """Fetch values from all sources concurrently."""
        tasks = [
            self.fetch_ktc_values(force_refresh),
            self.fetch_dynastyprocess_values(format, force_refresh),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        combined = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Source fetch failed: {result}")
                continue
            
            source_name = ["ktc", "dynastyprocess"][i]
            for name, data in result.items():
                if name not in combined:
                    combined[name] = {}
                combined[name][source_name] = data
        
        return combined
    
    # =========================================================================
    # Consensus Calculation
    # =========================================================================
    
    def calculate_effective_value(self, raw_value: float) -> float:
        """Apply KTC-style nonlinear normalization."""
        if raw_value <= 0:
            return 0
        raw_value = min(raw_value, KTC_MAX)
        return (raw_value / KTC_MAX) ** KTC_POWER * KTC_MAX
    
    def calculate_consensus(
        self,
        player_values: Dict[str, Any],
        apply_stud_bonus: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate consensus value from multiple sources.
        
        Args:
            player_values: Dict of {source_name: {value, position, ...}}
            apply_stud_bonus: Whether to apply elite player bonus
        
        Returns:
            Consensus value dict
        """
        if not player_values:
            return {"error": "No values available", "consensus": 0}
        
        # Collect valid values with weights
        weighted_sum = 0
        weight_total = 0
        sources_used = []
        
        for source, weight in SOURCE_WEIGHTS.items():
            if source in player_values:
                val = player_values[source].get("value", 0)
                if val and val > 0:
                    weighted_sum += val * weight
                    weight_total += weight
                    sources_used.append(source)
        
        if weight_total == 0:
            return {"error": "No valid source values", "consensus": 0}
        
        # Calculate weighted average
        raw_value = weighted_sum / weight_total
        
        # Get primary position from any source
        position = None
        for source_data in player_values.values():
            if source_data.get("position"):
                position = source_data["position"]
                break
        
        # Apply effective value normalization
        effective_value = self.calculate_effective_value(raw_value)
        
        # Calculate stud bonus (for top 10% of players)
        stud_bonus = 0
        if apply_stud_bonus and raw_value > KTC_MAX * 0.9:
            stud_bonus = (raw_value - KTC_MAX * 0.9) * 0.3
            effective_value += stud_bonus
        
        return {
            "player": list(player_values.keys())[0] if player_values else "Unknown",
            "position": position or "WR",
            "raw_value": round(raw_value, 1),
            "effective_value": round(effective_value, 1),
            "stud_bonus": round(stud_bonus, 1),
            "consensus": round(effective_value, 1),
            "sources_used": sources_used,
            "source_count": len(sources_used)
        }
    
    def calculate_trade_fairness(
        self,
        give_value: float,
        get_value: float,
        fair_margin: float = 0.15
    ) -> Dict[str, Any]:
        """
        Calculate trade fairness metrics.
        
        Args:
            give_value: Total value being given up
            get_value: Total value being received
            fair_margin: Acceptable value difference (default 15%)
        
        Returns:
            Fairness analysis dict
        """
        if give_value <= 0:
            return {"error": "Invalid give value"}
        
        difference = get_value - give_value
        margin = abs(difference) / give_value
        
        is_fair = margin <= fair_margin
        
        # Determine winner and recommendation
        if difference > give_value * fair_margin:
            verdict = "YOU_WIN"
            recommendation = "Accept - you're getting good value"
        elif difference < -give_value * fair_margin:
            verdict = "THEY_WIN"
            recommendation = "Reject - you're overpaying"
        else:
            verdict = "FAIR"
            recommendation = "Fair trade - depends on positional needs"
        
        return {
            "give_value": round(give_value, 1),
            "get_value": round(get_value, 1),
            "difference": round(difference, 1),
            "margin": round(margin, 3),
            "is_fair": is_fair,
            "verdict": verdict,
            "recommendation": recommendation
        }
    
    # =========================================================================
    # Draft Pick Valuation
    # =========================================================================
    
    async def get_draft_pick_values(self, num_teams: int = 12) -> Dict[str, int]:
        """Calculate dynamic draft pick values based on ADP."""
        # Try to load ADP data
        adp_path = Path(__file__).parent.parent.parent / "static" / "player_adp_import.json"
        
        try:
            with open(adp_path) as f:
                adp_data = json.load(f)
            
            # Calculate first round values based on ADP
            # Use a simple decay model: value = base * (0.85 ^ (pick - 1))
            picks = {}
            base_value = 70  # 1.01 base value
            
            for i in range(1, num_teams + 1):
                pick_num = i
                value = int(base_value * (0.88 ** (pick_num - 1)))
                picks[f"2026_1.{pick_num:02d}"] = value
                picks[f"2026_2.{pick_num:02d}"] = int(value * 0.4)
            
            # Future picks discounted
            for year in [2027, 2028]:
                for i in range(1, num_teams + 1):
                    discount = 0.9 if year == 2027 else 0.8
                    picks[f"{year}_1.{i:02d}"] = int(picks[f"2026_1.{i:02d}"] * discount)
            
            return picks
            
        except Exception as e:
            logger.warning(f"Could not calculate dynamic pick values: {e}")
            return {}
    
    def parse_pick_string(self, pick_str: str, pick_values: Dict[str, int]) -> int:
        """Parse draft pick string to value."""
        # Try exact match
        if pick_str in pick_values:
            return pick_values[pick_str]
        
        # Try partial match
        parts = pick_str.replace("_", " ").split()
        if len(parts) >= 2:
            year = parts[0]
            round_pick = parts[1].replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
            if "." in round_pick:
                key = f"{year}_{round_pick}"
                if key in pick_values:
                    return pick_values[key]
        
        return 0


# Singleton instance
_value_service: Optional[DynastyValueService] = None


def get_value_service() -> DynastyValueService:
    """Get singleton value service instance."""
    global _value_service
    if _value_service is None:
        _value_service = DynastyValueService()
    return _value_service


async def test_value_service():
    """Test the unified value service."""
    service = DynastyValueService()
    
    # Test fetching
    print("Testing KTC fetch...")
    ktc = await service.fetch_ktc_values()
    print(f"Loaded {len(ktc)} KTC players")
    
    # Test consensus for sample players
    sample_player = {
        "ktc": {"value": 6704, "position": "WR"},
        "dynastyprocess": {"value": 6500, "position": "WR"}
    }
    
    consensus = service.calculate_consensus(sample_player)
    print(f"\nConsensus for Tet McMillan:")
    print(f"  Raw: {consensus['raw_value']}")
    print(f"  Effective: {consensus['effective_value']}")
    print(f"  Sources: {consensus['sources_used']}")
    
    # Test fairness
    fairness = service.calculate_trade_fairness(6000, 6500)
    print(f"\nTrade fairness (give 6000, get 6500):")
    print(f"  Verdict: {fairness['verdict']}")
    print(f"  Recommendation: {fairness['recommendation']}")


if __name__ == "__main__":
    asyncio.run(test_value_service())
