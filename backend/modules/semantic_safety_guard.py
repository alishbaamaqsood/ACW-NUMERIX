"""
semantic_safety_guard.py — Semantic Safety Guard for ACW
==========================================================

Protects critical information from being filtered during context compression.
Ensures numbers, dates, names, constraints, and negations are preserved.

Features:
  • Critical token detection (numbers, dates, names, constraints)
  • Semantic importance scoring
  • Preservation rate calculation
  • Safety validation before compression
  • Recovery of dropped critical chunks

Place in: numerix-na-webapp/backend/modules/semantic_safety_guard.py
"""

import re
from typing import List, Dict, Tuple, Set
from enum import Enum


class CriticalTokenType(Enum):
    """Types of critical tokens that must be preserved"""
    NUMBER = "number"
    DATE = "date"
    NAME = "name"
    INSTRUCTION = "instruction"
    CONSTRAINT = "constraint"
    NEGATION = "negation"
    CITATION = "citation"
    MEASUREMENT = "measurement"


class SemanticSafetyGuard:
    """
    Validates and protects critical information during context compression.
    
    Preservation Categories:
    ────────────────────────
    1. NUMBERS (20 points each)
       - Percentages, decimals, integers, scientific notation
       - Examples: 42, 3.14, 50%, 1.5e-3
    
    2. DATES & TIMES (15 points each)
       - Absolute: "2024-09-12", "September 12", "Q3 2024"
       - Relative: "yesterday", "next week", "3 days ago"
    
    3. NAMES & ENTITIES (15 points each)
       - Proper nouns, people, places, organizations
       - Model names, chemical formulas, product names
    
    4. CONSTRAINTS (20 points each)
       - "must not", "only", "exclude", "cannot"
       - Negations: "not", "never", "no"
       - Conditionals: "if", "unless", "except"
    
    5. INSTRUCTIONS (15 points each)
       - Imperative verbs: "use", "apply", "set", "calculate"
       - Step markers: "first", "then", "finally"
    
    6. CITATIONS (10 points each)
       - References, sources, equations, formulas
       - [1], "cite:", "according to", page numbers
    
    7. MEASUREMENTS & UNITS (15 points each)
       - "kg", "meters", "celsius", "mph"
       - With values: "5kg", "100m", "-20°C"
    """
    
    # Regex patterns for critical token detection
    PATTERNS = {
        "number": r'-?\d+\.?\d*(?:[eE][+-]?\d+)?|[0-9]+%',
        "date": r'\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}|Q[1-4] \d{4}',
        "time": r'\d{1,2}:\d{2}(?::\d{2})?(?:AM|PM|am|pm)?',
        "name": r'\b[A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+\b',  # Proper nouns
        "instruction": r'\b(?:use|apply|set|calculate|compute|derive|solve|find|determine|prove|show|demonstrate|verify)\b',
        "constraint": r'\b(?:must not|cannot|only|exclude|except|unless|if|not|never|no|without)\b',
        "citation": r'\[\d+\]|cite:|according to|see page|section \d+',
        "measurement": r'\d+(?:\.\d+)?\s*(?:kg|g|m|cm|km|°C|°F|mph|m/s|V|A|W|Hz|Pa|J)',
    }
    
    # Constraint keywords with high protection level
    STRICT_CONSTRAINTS = {
        'not', 'never', 'must not', 'cannot', 'no', 'exclude',
        'only', 'except', 'unless', 'without', 'no longer'
    }
    
    # Instruction keywords requiring full context
    CRITICAL_INSTRUCTIONS = {
        'calculate', 'solve', 'derive', 'prove', 'verify', 'determine',
        'compute', 'apply', 'use', 'set', 'must', 'always', 'required'
    }
    
    def __init__(self):
        """Initialize safety guard"""
        self.critical_tokens_found = []
        self.preservation_rate = 1.0
    
    # Domain vocabulary that should NOT count as a "critical name" — these are
    # ordinary method/module terms that appear constantly in a numerical-methods
    # knowledge base, not people/places/entities whose exact wording must be
    # preserved. Without this filter, the "name" pattern flags almost every
    # capitalized method name (Bisection, Newton-Raphson, Simpson's Rule...)
    # as critical, which makes preservation_rate fail on nearly every chunk.
    DOMAIN_NAME_WHITELIST = {
        "bisection", "newton raphson", "newton-raphson", "false position",
        "regula falsi", "fixed point", "fixed-point", "simpson", "trapezoidal",
        "euler", "heun", "runge kutta", "runge-kutta", "lagrange",
        "newton forward", "newton backward", "newton divided", "doolittle",
        "crout", "numerix", "root finder", "error analyzer", "interpolator",
        "differentiator", "integrator", "ode solver", "linear systems",
    }

    def _is_domain_term(self, name_match: str) -> bool:
        return name_match.strip().lower() in self.DOMAIN_NAME_WHITELIST

    def scan_chunk_for_critical_tokens(self, chunk: str) -> Dict[str, List[str]]:
        """
        Scan a chunk for critical tokens.
        
        Returns:
            Dictionary mapping token type to found tokens
        """
        critical_tokens = {}
        
        for token_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, chunk, re.IGNORECASE)
            if token_type == "name":
                # Drop known domain/method terms — they're not the kind of
                # "name" this guard is meant to protect (see whitelist above).
                matches = [m for m in matches if not self._is_domain_term(m)]
            if matches:
                critical_tokens[token_type] = matches
        
        return critical_tokens
    
    def calculate_semantic_importance(self, chunk: str) -> float:
        """
        Calculate semantic importance score (0-1) for a chunk.
        
        Factors:
        - Number of critical tokens
        - Type of critical tokens
        - Presence of constraints or instructions
        """
        score = 0.0
        max_score = 100
        
        # Scan for critical tokens
        critical_tokens = self.scan_chunk_for_critical_tokens(chunk)
        
        # Points for each token type
        for token_type, tokens in critical_tokens.items():
            if token_type == "number":
                score += len(tokens) * 20  # Numbers: highest importance
            elif token_type == "date":
                score += len(tokens) * 15
            elif token_type == "name":
                score += len(tokens) * 15
            elif token_type == "measurement":
                score += len(tokens) * 15
            elif token_type == "instruction":
                score += len(tokens) * 15
            elif token_type == "constraint":
                score += len(tokens) * 20  # Constraints: critical
            elif token_type == "negation":
                score += len(tokens) * 20
            elif token_type == "citation":
                score += len(tokens) * 10
        
        # Bonus points for specific critical keywords
        chunk_lower = chunk.lower()
        for constraint in self.STRICT_CONSTRAINTS:
            if constraint in chunk_lower:
                score += 25  # Major boost for strict constraints
                break
        
        for instruction in self.CRITICAL_INSTRUCTIONS:
            if instruction in chunk_lower:
                score += 20
                break
        
        # Normalize to 0-1
        importance = min(score / max_score, 1.0)
        return importance
    
    def validate_compression_safety(
        self,
        original_chunks: List[Dict],
        filtered_chunks: List[Dict],
        threshold: float = 0.8
    ) -> Tuple[bool, Dict]:
        """
        Validate that compression doesn't lose critical information.
        
        Args:
            original_chunks: Full list of chunks
            filtered_chunks: Compressed chunk list
            threshold: Minimum preservation rate (default 0.8 = 80%)
        
        Returns:
            (is_safe: bool, metadata: dict)
        """
        # Scan all chunks for critical tokens
        original_tokens = {}
        filtered_tokens = {}
        
        for chunk in original_chunks:
            content = chunk.get('content', '')
            tokens = self.scan_chunk_for_critical_tokens(content)
            for token_type, found in tokens.items():
                if token_type not in original_tokens:
                    original_tokens[token_type] = set()
                original_tokens[token_type].update(found)
        
        for chunk in filtered_chunks:
            content = chunk.get('content', '')
            tokens = self.scan_chunk_for_critical_tokens(content)
            for token_type, found in tokens.items():
                if token_type not in filtered_tokens:
                    filtered_tokens[token_type] = set()
                filtered_tokens[token_type].update(found)
        
        # Calculate preservation rate
        total_original = sum(len(v) for v in original_tokens.values())
        total_preserved = sum(len(v) for v in filtered_tokens.values())
        
        if total_original == 0:
            preservation_rate = 1.0
        else:
            preservation_rate = total_preserved / total_original
        
        # Check for missing critical constraints
        missing_constraints = False
        if 'constraint' in original_tokens and 'constraint' in filtered_tokens:
            missing = original_tokens['constraint'] - filtered_tokens['constraint']
            if missing and any(c in self.STRICT_CONSTRAINTS for c in missing):
                missing_constraints = True
        
        # Determine safety
        is_safe = (preservation_rate >= threshold) and not missing_constraints
        
        metadata = {
            "preservation_rate": preservation_rate,
            "total_critical_tokens": total_original,
            "preserved_tokens": total_preserved,
            "missing_constraints": missing_constraints,
            "is_safe": is_safe,
            "token_breakdown": {
                "original": {k: len(v) for k, v in original_tokens.items()},
                "preserved": {k: len(v) for k, v in filtered_tokens.items()},
            }
        }
        
        return is_safe, metadata
    
    def identify_critical_chunks(
        self,
        chunks: List[Dict],
        top_k: int = 3
    ) -> List[Dict]:
        """
        Identify chunks with highest semantic importance (critical tokens).
        
        Returns:
            List of chunks sorted by importance, descending
        """
        scored_chunks = []
        
        for chunk in chunks:
            content = chunk.get('content', '')
            importance = self.calculate_semantic_importance(content)
            
            scored_chunks.append({
                **chunk,
                "importance_score": importance,
                "critical_tokens": self.scan_chunk_for_critical_tokens(content)
            })
        
        # Sort by importance, descending
        scored_chunks.sort(key=lambda x: x['importance_score'], reverse=True)
        
        return scored_chunks[:top_k]
    
    def generate_safety_report(
        self,
        chunks: List[Dict],
        filtered_chunks: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive safety report on compression.
        
        Returns:
            Dictionary with detailed metrics
        """
        is_safe, validation = self.validate_compression_safety(chunks, filtered_chunks)
        
        critical_chunks = self.identify_critical_chunks(chunks, top_k=5)
        
        return {
            "overall_safe": is_safe,
            "preservation_metrics": validation,
            "critical_chunks": [
                {
                    "title": c.get('title', 'Untitled'),
                    "importance_score": c.get('importance_score', 0),
                    "critical_tokens": c.get('critical_tokens', {})
                }
                for c in critical_chunks
            ],
            "recommendations": self._generate_recommendations(is_safe, validation)
        }
    
    def _generate_recommendations(self, is_safe: bool, validation: Dict) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if not is_safe:
            if validation['missing_constraints']:
                recommendations.append(
                    "⚠️ CRITICAL: Missing constraint keywords. Expand context to include "
                    "all 'not', 'never', 'must not' statements."
                )
            
            if validation['preservation_rate'] < 0.6:
                recommendations.append(
                    f"⚠️ WARNING: Only {validation['preservation_rate']*100:.1f}% of critical tokens preserved. "
                    "Reduce compression aggressiveness."
                )
        
        if validation['preservation_rate'] < 0.8:
            recommendations.append(
                "ℹ️ Consider using MODERATE compression instead of AGGRESSIVE."
            )
        
        if not recommendations:
            recommendations.append(
                "✓ Compression is safe. All critical information preserved."
            )
        
        return recommendations


# Example usage
if __name__ == "__main__":
    guard = SemanticSafetyGuard()
    
    test_chunk = """
    To solve this equation, you must NOT use approximation methods.
    The exact solution is x = 3.14 (±0.01), calculated on 2024-09-12.
    Only Newton-Raphson method is acceptable. Reference [1] shows that
    values must be in Celsius (°C), never Fahrenheit.
    """
    
    print("Critical Tokens Found:")
    tokens = guard.scan_chunk_for_critical_tokens(test_chunk)
    for token_type, found in tokens.items():
        print(f"  {token_type}: {found}")
    
    print(f"\nSemantic Importance Score: {guard.calculate_semantic_importance(test_chunk):.2f}")
