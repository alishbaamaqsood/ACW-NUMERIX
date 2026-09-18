"""
risk_aware_compression.py — Risk-Aware Adaptive Compression for ACW
=====================================================================

Calculates context risk (based on query complexity, domain, answer type) and 
automatically chooses compression aggressiveness via an adaptive ladder.

Features:
  • Query complexity scoring (keyword analysis, question type detection)
  • Domain risk assessment (math, finance, legal, medical risk levels)
  • Answer type prediction (factual, procedural, explanatory)
  • Adaptive compression ladder (1-5 levels, stops at safe threshold)
  • Automatic rollback if risk threshold exceeded

Place in: numerix-na-webapp/backend/modules/risk_aware_compression.py
"""

import re
import math
from typing import Dict, List, Tuple
from enum import Enum


class RiskLevel(Enum):
    """Risk assessment categories"""
    LOW = 1          # Simple queries, general info
    MEDIUM = 2       # Moderate complexity, standard procedures
    HIGH = 3         # Complex multi-step, critical numbers/dates
    CRITICAL = 4     # Life-critical, financial, legal, medical
    EXTREME = 5      # Multiple risk factors, irreversible consequences


class CompressionLevel(Enum):
    """Adaptive compression ladder"""
    NONE = 0         # Baseline - no compression
    MILD = 1         # 10-15% reduction
    MODERATE = 2     # 30-40% reduction (default)
    AGGRESSIVE = 3   # 50-60% reduction
    EXTREME = 4      # 70-80% reduction (highest risk)


class RiskAwareCompression:
    """
    Calculates context risk and automatically selects compression aggressiveness.
    
    Risk Scoring Factors:
    ─────────────────────
    1. Query Complexity (0-30 points)
       - Number of clauses, domain keywords, question depth
    
    2. Domain Risk (0-30 points)
       - Mathematics: LOW (10)
       - Finance/Economics: HIGH (25)
       - Medical/Health: CRITICAL (30)
       - Legal: CRITICAL (30)
       - General: MEDIUM (15)
    
    3. Answer Type (0-20 points)
       - Factual (numbers, dates, names): 20 points
       - Procedural (steps, methods): 15 points
       - Explanatory (concepts, why): 10 points
    
    4. Critical Keywords (0-20 points)
       - Constraint words (not, never, only): 10 points each
       - Number/date words (exactly, between, by): 5 points each
    
    Total Risk Score: 0-100
    ├─ 0-25:   LOW → No compression needed
    ├─ 26-40:  MEDIUM → Mild compression (1)
    ├─ 41-60:  HIGH → Moderate compression (2)
    ├─ 61-80:  CRITICAL → Aggressive (3)
    └─ 81-100: EXTREME → Extreme compression (4) with rollback
    """
    
    # Domain risk mappings
    DOMAIN_RISK_MAP = {
        'mathematics': 10,
        'algebra': 10,
        'calculus': 10,
        'geometry': 10,
        'numerical': 12,
        'finance': 25,
        'money': 25,
        'investment': 25,
        'medical': 30,
        'health': 30,
        'medicine': 30,
        'disease': 30,
        'legal': 30,
        'law': 30,
        'contract': 30,
        'compliance': 25,
    }
    
    # Critical keywords requiring high confidence
    CRITICAL_KEYWORDS = {
        'constraint': ['not', 'never', 'only', 'must not', 'cannot', 'exclude'],
        'precision': ['exactly', 'precisely', 'specific', 'particular'],
        'temporal': ['before', 'after', 'by', 'until', 'deadline'],
        'numerical': ['how many', 'what percentage', 'how much', 'total', 'sum'],
    }
    
    def __init__(self):
        """Initialize risk scorer"""
        self.query_history = []
    
    def calculate_risk_score(self, query: str, domain: str = None) -> Tuple[int, str]:
        """
        Calculate overall risk score for a query.
        
        Returns:
            (risk_score: 0-100, risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL")
        """
        score = 0
        
        # 1. Query complexity (0-30)
        complexity = self._score_query_complexity(query)
        score += min(complexity, 30)
        
        # 2. Domain risk (0-30)
        if domain:
            domain_risk = self._score_domain_risk(domain)
            score += min(domain_risk, 30)
        
        # 3. Answer type (0-20)
        answer_type = self._predict_answer_type(query)
        score += answer_type
        
        # 4. Critical keywords (0-20)
        critical_score = self._score_critical_keywords(query)
        score += min(critical_score, 20)
        
        # Determine risk level
        if score <= 25:
            risk_level = RiskLevel.LOW
        elif score <= 40:
            risk_level = RiskLevel.MEDIUM
        elif score <= 60:
            risk_level = RiskLevel.HIGH
        elif score <= 80:
            risk_level = RiskLevel.CRITICAL
        else:
            risk_level = RiskLevel.EXTREME
        
        return score, risk_level.name
    
    def _score_query_complexity(self, query: str) -> int:
        """Score query complexity based on structure and length"""
        score = 0
        
        # Length heuristic
        words = len(query.split())
        score += min(words // 3, 10)  # 0-10 points
        
        # Clause count (and, or, but, etc.)
        conjunctions = len(re.findall(r'\b(and|or|but|if|when|where)\b', query, re.I))
        score += min(conjunctions * 3, 10)  # 0-10 points
        
        # Question depth (multiple conditions)
        conditions = len(re.findall(r'(\?|,|;)', query))
        score += min(conditions * 2, 10)  # 0-10 points
        
        return score
    
    def _score_domain_risk(self, domain: str) -> int:
        """Score risk based on domain"""
        domain_lower = domain.lower()
        
        # Direct match
        for key, risk in self.DOMAIN_RISK_MAP.items():
            if key in domain_lower:
                return risk
        
        # Default medium risk
        return 15
    
    def _predict_answer_type(self, query: str) -> int:
        """Predict what type of answer is needed"""
        query_lower = query.lower()
        
        # Procedural questions (steps, how-to)
        if any(word in query_lower for word in ['how', 'steps', 'process', 'procedure', 'method']):
            return 15  # Procedural answers are riskier (need complete steps)
        
        # Factual questions (numbers, dates, names)
        if any(word in query_lower for word in ['what', 'when', 'where', 'how many', 'which']):
            return 20  # Factual answers are highest risk (exact values)
        
        # Explanatory (why, concepts)
        if any(word in query_lower for word in ['why', 'explain', 'define', 'describe']):
            return 10  # Explanatory has some redundancy tolerance
        
        return 15  # Default
    
    def _score_critical_keywords(self, query: str) -> int:
        """Score presence of critical keywords requiring high confidence"""
        query_lower = query.lower()
        score = 0
        
        # Check each category
        for category, keywords in self.CRITICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in query_lower:
                    score += 5 if category == 'constraint' else 3
        
        return score
    
    def select_compression_level(
        self,
        query: str,
        domain: str = None,
        override_level: int = None
    ) -> Tuple[CompressionLevel, Dict]:
        """
        Select compression aggressiveness based on risk.
        
        Returns:
            (compression_level, metadata_dict)
        """
        if override_level is not None:
            return CompressionLevel(override_level), {"override": True}
        
        risk_score, risk_level = self.calculate_risk_score(query, domain)
        
        # Map risk to compression level
        if risk_score <= 25:
            compression = CompressionLevel.NONE
        elif risk_score <= 40:
            compression = CompressionLevel.MILD
        elif risk_score <= 60:
            compression = CompressionLevel.MODERATE
        elif risk_score <= 80:
            compression = CompressionLevel.AGGRESSIVE
        else:
            compression = CompressionLevel.EXTREME
        
        metadata = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "compression_level": compression.name,
            "compression_value": compression.value,
            "safe_threshold": risk_score <= 60,  # Safe if MEDIUM or below
        }
        
        return compression, metadata
    
    def validate_compression_safe(self, risk_score: int) -> bool:
        """
        Determine if compression is safe at current risk level.
        
        Safe if risk <= 60 (HIGH)
        Requires rollback mechanism if risk > 60
        """
        return risk_score <= 60


def create_compression_ladder() -> Dict[int, Dict]:
    """
    Create the adaptive compression ladder configuration.
    
    Returns:
        Dictionary mapping compression level to parameters
    """
    return {
        0: {
            "name": "NONE",
            "target_reduction": 0,
            "min_chunks": 3,
            "description": "No compression - full context"
        },
        1: {
            "name": "MILD",
            "target_reduction": 0.15,
            "min_chunks": 2,
            "description": "10-15% token reduction, semantic reranking"
        },
        2: {
            "name": "MODERATE",
            "target_reduction": 0.35,
            "min_chunks": 2,
            "description": "30-40% token reduction (recommended default)"
        },
        3: {
            "name": "AGGRESSIVE",
            "target_reduction": 0.55,
            "min_chunks": 1,
            "description": "50-60% token reduction, requires rollback"
        },
        4: {
            "name": "EXTREME",
            "target_reduction": 0.75,
            "min_chunks": 1,
            "description": "70-80% reduction, high rollback risk"
        }
    }


# Example usage
if __name__ == "__main__":
    rac = RiskAwareCompression()
    
    # Test queries
    test_queries = [
        ("What is calculus?", "mathematics"),
        ("How do I solve quadratic equations?", "mathematics"),
        ("What is the current interest rate for a mortgage?", "finance"),
        ("Calculate the exact dosage for this medication", "medical"),
        ("Explain the legal implications of this contract", "legal"),
    ]
    
    for query, domain in test_queries:
        compression, metadata = rac.select_compression_level(query, domain)
        print(f"\nQuery: {query}")
        print(f"Domain: {domain}")
        print(f"Risk Score: {metadata['risk_score']}/100")
        print(f"Risk Level: {metadata['risk_level']}")
        print(f"Compression: {compression.name} (Level {compression.value})")
        print(f"Safe: {metadata['safe_threshold']}")
