"""
Dynasty Values Service - Multi-source player value loading.

Loads dynasty trade values from:
- DynastyProcess (primary - compliant)
- FantasyPros
- Draft Sharks
- Footballguys

Stores in player_values table for blending/consensus calculations.
"""
import asyncio
import csv
import json
import logging
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx

logger = logging.getLogger(__name__)

# Data source configs
SOURCES = {
    "dynasty_process": {
        "url": "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv",
        "formats": ["1qb", "2qb"],  # value_1qb, value_2qb columns
        "cache_hours": 168,  # Weekly update
    },
    # FantasyPros and others - add later if needed
}


class DynastyValuesService:
    """Service for loading and managing dynasty player values."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "dynastydroid" / "values"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def fetch_dynasty_process(self, format: str = "2qb") -> Dict[str, int]:
        """
        Fetch values from DynastyProcess CSV.
        
        Args:
            format: "1qb" or "2qb" (superflex)
            
        Returns:
            Dict mapping player_name -> value
        """
        url = SOURCES["dynasty_process"]["url"]
        values = {}
        value_col = f"value_{format}"  # value_1qb or value_2qb
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse CSV
                reader = csv.DictReader(StringIO(response.text))
                for row in reader:
                    name = row.get("player", "").strip()
                    value = row.get(value_col, 0)
                    if name and value:
                        try:
                            values[name] = int(float(value))
                        except ValueError:
                            pass
                
                logger.info(f"Loaded {len(values)} values from DynastyProcess ({format})")
                return values
                
        except Exception as e:
            logger.error(f"Failed to fetch DynastyProcess: {e}")
            return {}
    
    def get_player_value(self, player_name: str, values_dict: Dict[str, int]) -> Optional[int]:
        """
        Look up player value by name.
        
        Args:
            player_name: Player full name
            values_dict: Values dict from source
            
        Returns:
            Value integer or None if not found
        """
        # Direct match
        if player_name in values_dict:
            return values_dict[player_name]
        
        # Try normalized match
        normalized = player_name.lower().strip()
        for name, value in values_dict.items():
            if name.lower() == normalized:
                return value
        
        return None
    
    async def load_all_sources(self, format: str = "sf") -> Dict[str, Dict[str, int]]:
        """
        Load values from all available sources.
        
        Args:
            format: "sf" or "1qb"
            
        Returns:
            Dict of source_name -> {player_name: value}
        """
        results = {}
        
        # DynastyProcess (primary)
        dp_values = await self.fetch_dynasty_process(format)
        if dp_values:
            results["dynasty_process"] = dp_values
        
        logger.info(f"Loaded {len(results)} value sources")
        return results
    
    def calculate_consensus(self, sources: Dict[str, Dict[str, int]], player_name: str) -> Optional[Dict[str, Any]]:
        """
        Calculate consensus value across sources.
        
        Args:
            sources: Dict of source -> values dict
            player_name: Player to look up
            
        Returns:
            Dict with avg_value, min, max, sources_count, or None
        """
        values = []
        for source_name, values_dict in sources.items():
            value = self.get_player_value(player_name, values_dict)
            if value is not None:
                values.append(value)
        
        if not values:
            return None
        
        return {
            "player_name": player_name,
            "avg_value": sum(values) // len(values),
            "min_value": min(values),
            "max_value": max(values),
            "range": max(values) - min(values),
            "sources_count": len(values),
            "sources": values
        }
    
    def generate_value_narrative(self, consensus: Dict[str, Any]) -> str:
        """
        Generate narrative text for value.
        
        Args:
            consensus: Dict from calculate_consensus
            
        Returns:
            Human-readable value description
        """
        if consensus is None:
            return "No value data available"
        
        avg = consensus["avg_value"]
        range_val = consensus["range"]
        sources = consensus["sources_count"]
        
        # Build narrative
        parts = [f"Consensus value: {avg}"]
        
        if range_val > 0:
            parts.append(f"(range {consensus['min_value']}-{consensus['max_value']})")
        
        if sources > 1:
            parts.append(f"from {sources} sources")
        
        # Value tier description
        if avg >= 80:
            tier = "elite"
        elif avg >= 50:
            tier = "starter"
        elif avg >= 30:
            tier = "rotation"
        elif avg >= 15:
            tier = "depth"
        else:
            tier = "roster fodder"
        
        parts.append(f"- {tier} tier")
        
        return " ".join(parts)


async def test_dynasty_values():
    """Test the dynasty values service."""
    service = DynastyValuesService()
    
    # Test fetching DynastyProcess
    values = await service.fetch_dynasty_process("sf")
    print(f"Loaded {len(values)} players from DynastyProcess")
    
    # Sample lookups
    sample_players = ["Justin Jefferson", "C.J. Stroud", "Bijan Robinson"]
    for player in sample_players:
        value = service.get_player_value(player, values)
        print(f"{player}: {value}")


if __name__ == "__main__":
    asyncio.run(test_dynasty_values())
