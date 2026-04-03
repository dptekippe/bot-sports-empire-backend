"""
Multi-source dynasty value blending - Phase 2
Blends: KTC + DynastyProcess + FantasyPros

Classes:
- PlayerValue: Dataclass for player value data
- SourceAdapter: Abstract base class for source adapters
- KTCAAdapter: KeepTradeCut adapter
- FantasyProsAdapter: FantasyPros ECR adapter
- DynastyProcessAdapter: DynastyProcess adapter
- ValueBlenderService: Orchestrates blending
"""

import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# === DATA CLASSES ===

@dataclass
class PlayerValue:
    """Player value data from a single source"""
    name: str
    position: str
    value: float
    source: str
    rank: Optional[int] = None
    adp: Optional[float] = None
    extra: Dict = field(default_factory=dict)


@dataclass
class BlendResult:
    """Result of blending multiple sources"""
    name: str
    position: str
    consensus: float
    sources_used: int
    breakdown: Dict[str, float]
    weights_applied: Dict[str, float]
    stud_bonus_applied: bool = False
    te_premium_applied: bool = False


# === SOURCE ADAPTERS ===

class SourceAdapter(ABC):
    """Abstract base class for value sources"""
    
    # Default weights for blending
    DEFAULT_WEIGHT = 0.0
    
    def __init__(self, weight: Optional[float] = None):
        self._weight = weight or self.DEFAULT_WEIGHT
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Source name"""
        pass
    
    @property
    def weight(self) -> float:
        """Blending weight for this source"""
        return self._weight
    
    def set_weight(self, weight: float) -> None:
        """Set blending weight"""
        self._weight = weight
    
    @abstractmethod
    async def fetch(self) -> List[PlayerValue]:
        """Fetch values from this source"""
        pass
    
    def normalize(self, raw_value: float, max_value: float) -> float:
        """Normalize to 0-100 scale"""
        if max_value <= 0:
            return 0.0
        return (raw_value / max_value) * 100.0
    
    def _load_static_json(self, filename: str) -> List[Dict]:
        """Load data from static JSON file"""
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "static",
            filename
        )
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return []


class KTCAAdapter(SourceAdapter):
    """KeepTradeCut adapter - crowdsourced dynasty values"""
    
    DEFAULT_WEIGHT = 0.30
    
    @property
    def name(self) -> str:
        return "KTC"
    
    async def fetch(self) -> List[PlayerValue]:
        """Load KTC values from static JSON"""
        data = self._load_static_json("ktc_values.json")
        results = []
        for item in data:
            results.append(PlayerValue(
                name=item.get('name', ''),
                position=item.get('pos', 'WR'),
                value=float(item.get('value', 0)),
                source=self.name,
                rank=item.get('rank'),
                extra=item
            ))
        return results


class FantasyProsAdapter(SourceAdapter):
    """FantasyPros adapter - ECR converted to values"""
    
    DEFAULT_WEIGHT = 0.20
    
    @property
    def name(self) -> str:
        return "FantasyPros"
    
    def ecr_to_value(self, ecr_rank: float, max_ecr: float = 200.0, max_value: float = 999.0) -> float:
        """Convert ECR rank to trade value using exponential decay"""
        if ecr_rank <= 0:
            return max_value
        # value = max * e^(-rank / decay)
        decay = 35.0  # Tunable decay factor
        return max_value * math.exp(-ecr_rank / decay)
    
    async def fetch(self) -> List[PlayerValue]:
        """Load FantasyPros ECR and convert to values"""
        data = self._load_static_json("fantasypros_values.json")
        results = []
        for item in data:
            ecr_rank = item.get('ecr', item.get('rank', 999))
            value = self.ecr_to_value(ecr_rank)
            results.append(PlayerValue(
                name=item.get('name', ''),
                position=item.get('pos', 'WR'),
                value=value,
                source=self.name,
                rank=int(ecr_rank) if ecr_rank < 999 else None
            ))
        return results


class DynastyProcessAdapter(SourceAdapter):
    """DynastyProcess adapter - data-driven values"""
    
    DEFAULT_WEIGHT = 0.50
    
    @property
    def name(self) -> str:
        return "DynastyProcess"
    
    async def fetch(self) -> List[PlayerValue]:
        """Load DynastyProcess values from static JSON"""
        data = self._load_static_json("dynastyprocess_values.json")
        results = []
        for item in data:
            results.append(PlayerValue(
                name=item.get('name', ''),
                position=item.get('pos', 'WR'),
                value=float(item.get('value', 0)),
                source=self.name,
                rank=item.get('rank'),
                extra=item
            ))
        return results


# === STUD BONUS LOGIC ===

STUD_THRESHOLD = 0.38  # % of opponent total
STUD_MULTIPLIER = 0.70  # How aggressively to reward


def calculate_stud_bonus(player_values: List[PlayerValue], other_side_total: float) -> tuple[float, bool]:
    """
    Calculate KTC-style stud dominance bonus.
    
    Returns: (bonus_amount, bonus_applied)
    """
    if not player_values or other_side_total <= 0:
        return 0.0, False
    
    max_player = max(player_values, key=lambda p: p.value)
    max_value = max_player.value
    other_total = other_side_total
    
    dominance_ratio = max_value / other_total
    
    if dominance_ratio > STUD_THRESHOLD:
        excess = max_value - (other_total * STUD_THRESHOLD)
        bonus = excess * STUD_MULTIPLIER
        return round(bonus), True
    
    return 0.0, False


# === VALUE BLENDER SERVICE ===

class ValueBlenderService:
    """
    Orchestrates multi-source value blending.
    
    Usage:
        service = ValueBlenderService()
        await service.initialize()
        result = await service.blend_player("Bijan Robinson")
    """
    
    def __init__(self, te_premium: bool = False):
        self.te_premium = te_premium
        self.TE_PREMIUM_MULTIPLIER = 1.65
        
        # Initialize adapters - 50/50 KTC/DynastyProcess blend (no FantasyPros)
        self.adapters: List[SourceAdapter] = [
            DynastyProcessAdapter(0.50),  # Data-driven values
            KTCAAdapter(0.50),             # Crowdsourced values
        ]
        
        # Cache for fetched values
        self._cache: Dict[str, List[PlayerValue]] = {}
        self._player_index: Dict[str, Dict[str, PlayerValue]] = {}
        
        # Max values for each source (for percentage normalization)
        self._max_values: Dict[str, float] = {}
    
    async def initialize(self) -> None:
        """Fetch values from all sources"""
        for adapter in self.adapters:
            values = await adapter.fetch()
            self._cache[adapter.name] = values
            
            # Track max value for percentage normalization
            if values:
                max_val = max(pv.value for pv in values)
                self._max_values[adapter.name] = max_val
            
            # Build player index
            for pv in values:
                if pv.name not in self._player_index:
                    self._player_index[pv.name] = {}
                self._player_index[pv.name][adapter.name] = pv
    
    def set_weight(self, source_name: str, weight: float) -> None:
        """Set weight for a specific source"""
        for adapter in self.adapters:
            if adapter.name == source_name:
                adapter.set_weight(weight)
                break
    
    async def blend_player(self, player_name: str, other_side_total: float = 0) -> BlendResult:
        """Blend values for a single player"""
        if player_name not in self._player_index:
            # Player not found - return 0
            return BlendResult(
                name=player_name,
                position="WR",
                consensus=0.0,
                sources_used=0,
                breakdown={},
                weights_applied={}
            )
        
        player_sources = self._player_index[player_name]
        position = list(player_sources.values())[0].position
        
        # Calculate weighted blend
        total_weight = 0.0
        weighted_sum = 0.0
        breakdown = {}
        weights_used = {}
        
        # Use percentage-based normalization for fair blending
        # KTC scale: 0-9999, DynastyProcess can go to ~10208
        OUTPUT_SCALE = 9999  # Normalize to KTC's max
        
        for adapter in self.adapters:
            if adapter.name in player_sources:
                pv = player_sources[adapter.name]
                max_val = self._max_values.get(adapter.name, 9999)
                # Normalize to percentage of max, then scale to output
                normalized_val = (pv.value / max_val) * OUTPUT_SCALE
                weight = adapter.weight
                total_weight += weight
                weighted_sum += normalized_val * weight
                breakdown[adapter.name] = pv.value  # Keep raw for display
                weights_used[adapter.name] = weight
        
        if total_weight > 0:
            consensus = weighted_sum / total_weight
        else:
            consensus = 0.0
        
        # Apply TE premium if enabled
        te_premium_applied = False
        if self.te_premium and position == "TE":
            consensus *= self.TE_PREMIUM_MULTIPLIER
            te_premium_applied = True
        
        return BlendResult(
            name=player_name,
            position=position,
            consensus=round(consensus, 1),
            sources_used=len(breakdown),
            breakdown={k: round(v, 1) for k, v in breakdown.items()},
            weights_applied=weights_used,
            te_premium_applied=te_premium_applied
        )
    
    async def blend_trade(
        self,
        give_players: List[str],
        get_players: List[str]
    ) -> Dict:
        """
        Evaluate a trade: blend values for both sides.
        
        Returns dict with give_total, get_total, net, winner
        """
        # Calculate totals
        give_total = 0.0
        get_total = 0.0
        give_details = []
        get_details = []
        
        for name in give_players:
            result = await self.blend_player(name)
            give_total += result.consensus
            give_details.append(result)
        
        for name in get_players:
            result = await self.blend_player(name)
            get_total += result.consensus
            get_details.append(result)
        
        # Apply stud bonus (only one side gets it)
        if give_total > get_total:
            # Give side has higher player - check for stud bonus
            bonus, applied = calculate_stud_bonus(
                [PlayerValue(name=d.name, position=d.position, value=d.consensus, source="blend") 
                 for d in give_details],
                get_total
            )
            if applied:
                give_total += bonus
        else:
            # Get side has higher player
            bonus, applied = calculate_stud_bonus(
                [PlayerValue(name=d.name, position=d.position, value=d.consensus, source="blend")
                 for d in get_details],
                give_total
            )
            if applied:
                get_total += bonus
        
        net = get_total - give_total
        winner = "even" if abs(net) < 50 else ("get" if net > 0 else "give")
        
        return {
            "give": {
                "players": give_details,
                "total": round(give_total, 1)
            },
            "get": {
                "players": get_details,
                "total": round(get_total, 1)
            },
            "net": round(net, 1),
            "winner": winner,
            "verdict": self._get_verdict(give_total, get_total, net)
        }
    
    def _get_verdict(self, give: float, get: float, net: float) -> str:
        """Generate verdict text"""
        if abs(net) < 50:
            return "Even trade"
        elif net > 0:
            pct = (net / give) * 100
            return f"Get side wins by {pct:.0f}%"
        else:
            pct = (abs(net) / get) * 100
            return f"Give side wins by {pct:.0f}%"
    
    def get_blend_summary(self) -> Dict:
        """Get summary of current blending configuration"""
        return {
            "sources": [a.name for a in self.adapters],
            "weights": {a.name: a.weight for a in self.adapters},
            "te_premium": self.te_premium,
            "players_cached": len(self._player_index)
        }


# === LEGACY FUNCTIONS (for backward compatibility) ===

async def get_consensus_values_v2(player_names: List[str], te_premium: bool = False) -> List[BlendResult]:
    """Legacy-compatible consensus values"""
    service = ValueBlenderService(te_premium=te_premium)
    await service.initialize()
    
    results = []
    for name in player_names:
        result = await service.blend_player(name)
        results.append(result)
    
    return results


# Standalone rank_to_value for FantasyPros ECR
def rank_to_value(rank: float, scale: float = 999, decay: float = 35) -> float:
    """Convert rank to value using exponential decay"""
    if rank <= 0:
        return scale
    return scale * math.exp(-rank / decay)
