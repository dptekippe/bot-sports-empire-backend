#!/usr/bin/env python3
"""
Bug Predictor Implementation
Based on skill_20260308_001_bug_predictor.json from MaxClaw/White Roger
"""

import re
import ast
import json
from typing import List, Dict, Any, Optional

class BugPredictor:
    """Predict common bug patterns in Python code."""
    
    def __init__(self):
        self.bug_patterns = {
            'index_error': [
                r'\[0\]',  # Accessing index 0 without length check
                r'\[-1\]',  # Accessing last element without length check
                r'\[len\(',  # Indexing at length (out of bounds)
                r'\.pop\(\)',  # pop() on potentially empty list
            ],
            'null_check': [
                r'\.\w+\(',  # Method call without null check
                r'\.\w+\s*=',  # Attribute assignment without null check
                r'if not \w+:',  # Missing explicit None check
            ],
            'type_error': [
                r'\+\s*["\']',  # String concatenation with non-string
                r'["\']\s*\+',  # String concatenation with non-string
                r'int\(["\']',  # int() on string that might not be numeric
                r'float\(["\']',  # float() on string that might not be numeric
            ],
            'logic_error': [
                r'global\s+\w+',  # Global variable usage
                r'=\s*\w+\s*[+\-*/]',  # Self-referential assignment
                r'while True:',  # Potential infinite loop
            ],
        }
        
        self.severity_mapping = {
            'index_error': 'high',
            'null_check': 'medium',
            'type_error': 'medium',
            'logic_error': 'medium',
            'memory_leak': 'high',
            'race_condition': 'critical',
        }
    
    def predict(self, code_snippet: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze code for common bug patterns.
        
        Args:
            code_snippet: Python code to analyze
            context: Optional context about the code
            
        Returns:
            Dictionary with bugs found and analysis summary
        """
        lines = code_snippet.split('\n')
        bugs_found = []
        
        for line_num, line in enumerate(lines, 1):
            line_bugs = self._analyze_line(line, line_num)
            bugs_found.extend(line_bugs)
        
        # Calculate overall confidence based on bug detection
        overall_confidence = self._calculate_confidence(bugs_found, len(lines))
        
        # Generate analysis summary
        analysis_summary = self._generate_summary(bugs_found, context)
        
        return {
            "bugs_found": bugs_found,
            "overall_confidence": overall_confidence,
            "analysis_summary": analysis_summary
        }
    
    def _analyze_line(self, line: str, line_num: int) -> List[Dict[str, Any]]:
        """Analyze a single line for bug patterns."""
        bugs = []
        
        for bug_type, patterns in self.bug_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line):
                    confidence = self._calculate_pattern_confidence(pattern, line)
                    bugs.append({
                        "type": bug_type,
                        "line": line_num,
                        "confidence": confidence,
                        "severity": self.severity_mapping.get(bug_type, 'medium')
                    })
                    break  # Only report first match per bug type per line
        
        return bugs
    
    def _calculate_pattern_confidence(self, pattern: str, line: str) -> float:
        """Calculate confidence score for a pattern match."""
        # Simple heuristic: longer patterns are more specific
        pattern_length = len(pattern)
        base_confidence = min(0.9, pattern_length / 20.0)
        
        # Adjust based on context
        if 'if' in line and 'else' not in line:
            # Conditional without else might be intentional
            return base_confidence * 0.8
        
        return base_confidence
    
    def _calculate_confidence(self, bugs_found: List[Dict], total_lines: int) -> float:
        """Calculate overall confidence score."""
        if not bugs_found:
            return 0.95  # High confidence if no bugs found
            
        # Average confidence of found bugs, weighted by severity
        severity_weights = {'low': 0.3, 'medium': 0.6, 'high': 0.8, 'critical': 0.9}
        weighted_sum = 0
        total_weight = 0
        
        for bug in bugs_found:
            weight = severity_weights.get(bug['severity'], 0.5)
            weighted_sum += bug['confidence'] * weight
            total_weight += weight
        
        if total_weight > 0:
            avg_confidence = weighted_sum / total_weight
        else:
            avg_confidence = 0.5
            
        # Adjust based on code length (longer code = more uncertainty)
        length_factor = min(1.0, 50.0 / max(total_lines, 1))
        
        return avg_confidence * length_factor
    
    def _generate_summary(self, bugs_found: List[Dict], context: Optional[str]) -> str:
        """Generate analysis summary."""
        if not bugs_found:
            return "No common bug patterns detected. Code appears clean."
        
        # Count bugs by type
        bug_counts = {}
        for bug in bugs_found:
            bug_type = bug['type']
            bug_counts[bug_type] = bug_counts.get(bug_type, 0) + 1
        
        # Generate summary
        summary_parts = [f"Found {len(bugs_found)} potential bug(s):"]
        
        for bug_type, count in bug_counts.items():
            severity = next((b['severity'] for b in bugs_found if b['type'] == bug_type), 'medium')
            summary_parts.append(f"- {count} {bug_type} ({severity} severity)")
        
        if context:
            summary_parts.append(f"Context: {context}")
        
        summary_parts.append("Note: This is an automated analysis. Manual review recommended.")
        
        return '\n'.join(summary_parts)

def main():
    """Test the bug predictor with example code snippets."""
    predictor = BugPredictor()
    
    # Test cases from the skill validation tests
    test_cases = [
        {
            "code_snippet": "if items[0]: pass",
            "context": "Index access without length check"
        },
        {
            "code_snippet": "try: x[1]\nexcept: pass",
            "context": "Exception handling"
        },
        {
            "code_snippet": "global x\ndef foo(): x = x + 1",
            "context": "Global variable usage"
        },
        {
            "code_snippet": "for i in range(len(items)):\n    if items[i] == target:\n        return i\nreturn -1",
            "context": "Linear search"
        },
        {
            "code_snippet": "result = []\nfor x in items:\n    result.append(x*2)",
            "context": "List comprehension alternative"
        }
    ]
    
    print("Bug Predictor Implementation Test")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Code: {test_case['code_snippet'][:50]}...")
        
        result = predictor.predict(test_case['code_snippet'], test_case['context'])
        
        print(f"Overall Confidence: {result['overall_confidence']:.2f}")
        print(f"Bugs Found: {len(result['bugs_found'])}")
        
        for bug in result['bugs_found']:
            print(f"  - Line {bug['line']}: {bug['type']} ({bug['severity']}) "
                  f"confidence: {bug['confidence']:.2f}")
        
        print(f"Summary: {result['analysis_summary'][:100]}...")

if __name__ == "__main__":
    main()