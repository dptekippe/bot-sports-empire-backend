#!/usr/bin/env python3
"""
Logic Chain Reducer Implementation
Based on skill_20260308_002_logic_chain_reducer.json from MaxClaw/White Roger
"""

import re
from typing import List, Dict, Any, Tuple

class LogicChainReducer:
    """Compress reasoning chains to minimal valid steps."""
    
    def __init__(self):
        # Common logical patterns and their reductions
        self.reduction_patterns = [
            # Syllogism patterns
            (r'All (\w+) are (\w+)\s*\.?\s*All (\w+) are (\w+)\s*\.?\s*Therefore all \1 are \4',
             r'All \1 are \2. All \2 are \3. Therefore all \1 are \3'),
            
            # Transitive property
            (r'(\w+) implies (\w+)\s*\.?\s*(\w+) implies (\w+)\s*\.?\s*Therefore \1 implies \4',
             r'\1 implies \2. \2 implies \3. Therefore \1 implies \3'),
            
            # Modus ponens
            (r'If (\w+) then (\w+)\s*\.?\s*\1\s*\.?\s*Therefore \2',
             r'If \1 then \2. \1. Therefore \2'),
            
            # Double negation elimination
            (r'Not not (\w+)\s*\.?\s*Therefore \1',
             r'\1'),
            
            # Identity elimination
            (r'(\w+) is \1',
             r''),  # Remove self-identity
        ]
        
        # Invalid patterns (common logical fallacies)
        self.invalid_patterns = [
            r'Some (\w+) are (\w+)\s*\.?\s*(\w+) is \1\s*\.?\s*Therefore \3 is \2',
            r'All (\w+) are (\w+)\s*\.?\s*(\w+) is \2\s*\.?\s*Therefore \3 is \1',
        ]
    
    def reduce(self, premises: List[str], goal: str) -> Dict[str, Any]:
        """
        Reduce reasoning chain to minimal valid steps.
        
        Args:
            premises: List of premise statements
            goal: Goal statement to reach
            
        Returns:
            Dictionary with minimal chain and analysis
        """
        # Start with original premises
        current_chain = premises.copy()
        redundant_steps_removed = 0
        
        # Apply reduction patterns
        for pattern, replacement in self.reduction_patterns:
            chain_text = '. '.join(current_chain)
            new_text = re.sub(pattern, replacement, chain_text, flags=re.IGNORECASE)
            
            if new_text != chain_text:
                # Pattern matched and was replaced
                new_chain = [s.strip() for s in new_text.split('. ') if s.strip()]
                redundant_steps_removed += len(current_chain) - len(new_chain)
                current_chain = new_chain
        
        # Check if goal can be reached
        logical_validity = self._check_validity(current_chain, goal)
        
        # Add conclusion if valid
        if logical_validity:
            if goal not in current_chain:
                current_chain.append(f"Therefore {goal}")
        else:
            current_chain.append(f"Cannot deduce: {self._get_invalid_reason(current_chain, goal)}")
        
        # Calculate confidence
        confidence = self._calculate_confidence(current_chain, premises, goal, logical_validity)
        
        return {
            "minimal_chain": current_chain,
            "redundant_steps_removed": redundant_steps_removed,
            "confidence": confidence,
            "logical_validity": logical_validity
        }
    
    def _check_validity(self, chain: List[str], goal: str) -> bool:
        """Check if goal can be logically deduced from chain."""
        chain_text = '. '.join(chain).lower()
        goal_lower = goal.lower()
        
        # Check for invalid patterns
        for pattern in self.invalid_patterns:
            if re.search(pattern, chain_text, re.IGNORECASE):
                return False
        
        # Simple validity checks
        if 'some' in chain_text and 'all' in goal_lower:
            # Can't deduce "all" from "some"
            return False
        
        if 'or' in chain_text and 'and' in goal_lower:
            # Can't deduce conjunction from disjunction
            return False
        
        # Check if goal is directly in chain or can be inferred
        if goal_lower in chain_text:
            return True
        
        # Check for transitive relationships
        if self._check_transitive(chain_text, goal_lower):
            return True
        
        return False
    
    def _check_transitive(self, chain_text: str, goal: str) -> bool:
        """Check for transitive relationships."""
        # Simple transitive check: A implies B, B implies C, therefore A implies C
        implies_pattern = r'(\w+) implies (\w+)'
        matches = re.findall(implies_pattern, chain_text, re.IGNORECASE)
        
        # Build implication graph
        graph = {}
        for a, b in matches:
            a = a.lower()
            b = b.lower()
            if a not in graph:
                graph[a] = []
            graph[a].append(b)
        
        # Check if goal follows transitively
        goal_parts = goal.split()
        if len(goal_parts) >= 3 and goal_parts[1] == 'implies':
            start = goal_parts[0].lower()
            end = goal_parts[2].lower()
            
            # Simple DFS to check reachability
            visited = set()
            stack = [start]
            
            while stack:
                current = stack.pop()
                if current == end:
                    return True
                if current in visited:
                    continue
                visited.add(current)
                if current in graph:
                    stack.extend(graph[current])
        
        return False
    
    def _get_invalid_reason(self, chain: List[str], goal: str) -> str:
        """Get reason why deduction is invalid."""
        chain_text = '. '.join(chain).lower()
        goal_lower = goal.lower()
        
        if 'some' in chain_text and 'all' in goal_lower:
            return "'some' doesn't mean 'all'"
        
        if 'or' in chain_text and 'and' in goal_lower:
            return "can't deduce conjunction from disjunction"
        
        if 'if' in chain_text and 'only if' not in chain_text and 'if and only if' in goal_lower:
            return "can't deduce biconditional from conditional"
        
        return "insufficient premises or logical fallacy"
    
    def _calculate_confidence(self, minimal_chain: List[str], 
                            original_premises: List[str], 
                            goal: str, 
                            validity: bool) -> float:
        """Calculate confidence score."""
        # Base confidence
        base_confidence = 0.9 if validity else 0.7
        
        # Adjust based on compression
        original_length = len(original_premises)
        minimal_length = len(minimal_chain)
        
        if original_length > 0:
            compression_ratio = 1.0 - (minimal_length / original_length)
            # More compression = slightly lower confidence (more aggressive reduction)
            compression_factor = 1.0 - (compression_ratio * 0.2)
            base_confidence *= compression_factor
        
        # Adjust based on chain complexity
        complexity = sum(len(step.split()) for step in minimal_chain)
        complexity_factor = min(1.0, 50.0 / max(complexity, 1))
        base_confidence *= complexity_factor
        
        return min(0.99, max(0.1, base_confidence))

def main():
    """Test the logic chain reducer with example arguments."""
    reducer = LogicChainReducer()
    
    # Test cases from the skill validation tests
    test_cases = [
        {
            "premises": ["All humans are mortal", "Socrates is human", "Socrates is Socrates"],
            "goal": "Socrates is mortal"
        },
        {
            "premises": ["If rain then wet", "If wet then slippery", "It rained"],
            "goal": "It is slippery"
        },
        {
            "premises": ["A implies B", "B implies C", "C implies D", "A"],
            "goal": "D"
        },
        {
            "premises": ["Some birds fly", "Penguin is bird"],
            "goal": "Penguin flies"
        },
        {
            "premises": ["All A are B", "All B are C"],
            "goal": "All A are C"
        }
    ]
    
    print("Logic Chain Reducer Implementation Test")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Premises: {test_case['premises']}")
        print(f"Goal: {test_case['goal']}")
        
        result = reducer.reduce(test_case['premises'], test_case['goal'])
        
        print(f"Logical Validity: {result['logical_validity']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Redundant Steps Removed: {result['redundant_steps_removed']}")
        print(f"Minimal Chain:")
        for step in result['minimal_chain']:
            print(f"  - {step}")

if __name__ == "__main__":
    main()