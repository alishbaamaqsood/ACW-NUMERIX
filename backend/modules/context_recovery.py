"""
context_recovery.py — Context Recovery & Rollback Mechanism for ACW
====================================================================

Implements the Compress → Generate → Evaluate → Recover pipeline.
If compressed context produces unreliable output, automatically restores
additional context and retries.

Pipeline:
  1. COMPRESS: Filter context using ACW
  2. GENERATE: Get LLM response with compressed context
  3. EVALUATE: Score response quality/confidence
  4. RECOVER: If quality < threshold, restore context and retry

Features:
  • Multi-stage confidence scoring
  • Automatic context restoration ladder
  • Retry logic with exponential backoff
  • Quality metrics tracking
  • Fallback to full context

Place in: numerix-na-webapp/backend/modules/context_recovery.py
"""

import re
import math
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ConfidenceLevel(Enum):
    """Response confidence assessment"""
    CRITICAL = 0      # Major issues - immediate rollback
    LOW = 1           # Poor quality - rollback recommended
    MODERATE = 2      # Acceptable but could be better
    HIGH = 3          # Good confidence - keep result
    VERY_HIGH = 4     # Excellent confidence - complete success


class RecoveryStage(Enum):
    """Rollback stages (from most aggressive to least)"""
    LEVEL_4_EXTREME = 4    # 70-80% compression
    LEVEL_3_AGGRESSIVE = 3 # 50-60% compression
    LEVEL_2_MODERATE = 2   # 30-40% compression (start here)
    LEVEL_1_MILD = 1       # 10-15% compression
    LEVEL_0_NONE = 0       # No compression (full context)


class ContextRecovery:
    """
    Implements automatic context recovery and retry logic.
    
    Pipeline States:
    ────────────────
    INITIAL → COMPRESSED (ACW applied)
             ↓
           GENERATE (LLM inference)
             ↓
           EVALUATE (quality check)
             ↓
           DECISION POINT
             ├→ Quality HIGH → COMPLETE (return response)
             ├→ Quality MODERATE → MONITOR (check for issues)
             └→ Quality LOW/CRITICAL → RECOVER (rollback)
    
    Recovery Ladder:
    ────────────────
    If RECOVER triggered, try progressively less compression:
    
    Current Level: 3 (AGGRESSIVE - 50-60% reduction)
         ↓ FAIL
    Try Level 2: (MODERATE - 30-40% reduction)
         ↓ If FAIL again
    Try Level 1: (MILD - 10-15% reduction)
         ↓ If FAIL again
    Try Level 0: (NONE - full context)
         ↓ If FAIL again
    FALLBACK: Return original response with confidence warning
    """
    
    def __init__(self):
        """Initialize recovery system"""
        self.retry_count = 0
        self.max_retries = 3
        self.recovery_history = []
    
    def evaluate_response_quality(
        self,
        query: str,
        response: str,
        context: str
    ) -> Tuple[ConfidenceLevel, float, Dict]:
        """
        Evaluate LLM response quality and confidence.
        
        Scoring Factors (0-100):
        ─────────────────────────
        1. Relevance (0-25 points)
           - Does response directly answer query?
           - Keyword overlap between query and response
        
        2. Completeness (0-25 points)
           - Does response cover main question?
           - Are all sub-questions addressed?
        
        3. Coherence (0-20 points)
           - Is response logically structured?
           - Proper grammar and sentence flow?
        
        4. Citation Quality (0-15 points)
           - References sources/chunks used
           - Numbers and claims are cited
        
        5. Confidence Signals (0-15 points)
           - Hedging language (maybe, probably) = negative
           - Definitive statements = positive
           - Acknowledgment of limitations = positive
        
        Returns:
            (confidence_level, score_0_to_1, metadata_dict)
        """
        score = 0
        metadata = {}
        
        # 1. Relevance scoring
        relevance = self._score_relevance(query, response, context)
        score += relevance
        metadata['relevance_score'] = relevance
        
        # 2. Completeness scoring
        completeness = self._score_completeness(query, response)
        score += completeness
        metadata['completeness_score'] = completeness
        
        # 3. Coherence scoring
        coherence = self._score_coherence(response)
        score += coherence
        metadata['coherence_score'] = coherence
        
        # 4. Citation scoring
        citations = self._score_citations(response, context)
        score += citations
        metadata['citation_score'] = citations
        
        # 5. Confidence signal scoring
        confidence_signals = self._score_confidence_signals(response)
        score += confidence_signals
        metadata['confidence_signal_score'] = confidence_signals
        
        # Normalize score
        max_score = 100
        normalized_score = min(score / max_score, 1.0)
        
        # Determine confidence level
        if normalized_score >= 0.85:
            confidence = ConfidenceLevel.VERY_HIGH
        elif normalized_score >= 0.70:
            confidence = ConfidenceLevel.HIGH
        elif normalized_score >= 0.55:
            confidence = ConfidenceLevel.MODERATE
        elif normalized_score >= 0.35:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.CRITICAL
        
        metadata['confidence_level'] = confidence.name
        metadata['overall_score'] = normalized_score
        metadata['total_score_raw'] = score
        
        return confidence, normalized_score, metadata
    
    def _score_relevance(self, query: str, response: str, context: str) -> float:
        """Score how relevant response is to query"""
        score = 0
        
        # Keyword overlap
        query_words = set(re.findall(r'\w+', query.lower()))
        response_words = set(re.findall(r'\w+', response.lower()))
        
        overlap = len(query_words & response_words) / max(len(query_words), 1)
        score += min(overlap * 25, 25)
        
        # Check if query is directly addressed
        query_type = self._detect_query_type(query)
        if query_type == "how_to":
            # Look for imperative verbs (steps)
            if re.search(r'\b(then|next|finally|step|first)\b', response, re.I):
                score += 5
        elif query_type == "factual":
            # Look for numbers/dates/specific facts
            if re.search(r'\d+|is |are |the ', response):
                score += 5
        
        return min(score, 25)
    
    def _score_completeness(self, query: str, response: str) -> float:
        """Score if response fully addresses the query"""
        score = 0
        
        # Check response length (should be substantive)
        if len(response.split()) < 20:
            return 5  # Too short - likely incomplete
        
        # Multi-part question completeness
        sub_questions = query.count('?')
        response_sentences = len(re.split(r'[.!?]', response))
        
        if sub_questions > 0:
            coverage = min(response_sentences / (sub_questions + 1), 1.0)
            score += coverage * 25
        else:
            # Single question - penalize if too brief
            if len(response.split()) > 50:
                score = 25
            else:
                score = 15
        
        return min(score, 25)
    
    def _score_coherence(self, response: str) -> float:
        """Score logical structure and readability"""
        score = 0
        
        # Check for proper sentence structure
        sentences = re.split(r'[.!?]', response)
        valid_sentences = [s for s in sentences if len(s.strip()) > 5]
        
        if len(valid_sentences) > 0:
            coherence_rate = len(valid_sentences) / (len(sentences) - 1)
            score += coherence_rate * 20
        
        # Check for transition words (good sign of organization)
        transitions = re.findall(
            r'\b(first|second|finally|moreover|however|therefore|thus|in conclusion)\b',
            response,
            re.I
        )
        if transitions:
            score += 5
        
        # Penalize for excessive hedging
        hedging = re.findall(r'\b(maybe|perhaps|possibly|might|could)\b', response, re.I)
        if len(hedging) > 3:
            score -= 3
        
        return min(max(score, 0), 20)
    
    def _score_citations(self, response: str, context: str) -> float:
        """Score if response references the provided context"""
        score = 0
        
        # Check for citation markers
        citations = re.findall(r'\[\d+\]|cite|reference', response, re.I)
        if citations:
            score += 8
        
        # Check if specific facts from context appear in response
        context_phrases = re.findall(r'\b\w{4,}\b', context)  # Words 4+ chars
        response_phrases = set(re.findall(r'\b\w{4,}\b', response.lower()))
        
        if context_phrases:
            phrase_overlap = len(set(context_phrases) & response_phrases)
            score += min(phrase_overlap / len(set(context_phrases)) * 7, 7)
        
        return min(score, 15)
    
    def _score_confidence_signals(self, response: str) -> float:
        """Score confidence indicators in response text"""
        score = 10  # Default: neutral confidence
        
        # Positive signals
        definitive = len(re.findall(r'\b(is |are |will |must )\b', response, re.I))
        score += min(definitive * 2, 5)
        
        # Acknowledge limitations
        if re.search(r'\b(however|but|limitation|caveat|note that)\b', response, re.I):
            score += 3
        
        # Negative signals (excessive hedging)
        hedging = len(re.findall(r'\b(maybe|perhaps|probably|might|could)\b', response, re.I))
        score -= min(hedging * 2, 5)
        
        # Quantified uncertainty
        if re.search(r'(\d+\s*%\s*(?:confident|likely))', response):
            score += 2
        
        return min(max(score, 0), 15)
    
    def _detect_query_type(self, query: str) -> str:
        """Detect the type of question"""
        query_lower = query.lower()
        
        if re.search(r'\b(how|steps|process|method)\b', query_lower):
            return "how_to"
        elif re.search(r'\b(what|when|where|which|why)\b', query_lower):
            return "factual"
        elif re.search(r'\b(explain|describe|define)\b', query_lower):
            return "explanatory"
        else:
            return "general"
    
    def should_recover(
        self,
        confidence_level: ConfidenceLevel,
        score: float,
        threshold: float = 0.55
    ) -> bool:
        """
        Determine if recovery (rollback) is needed.
        
        Args:
            confidence_level: Evaluated confidence
            score: Quality score 0-1
            threshold: Minimum acceptable score (default 0.55)
        
        Returns:
            True if recovery should be triggered
        """
        return (
            confidence_level in [ConfidenceLevel.CRITICAL, ConfidenceLevel.LOW] or
            score < threshold
        )

    def should_abstain(
        self,
        confidence_level: ConfidenceLevel,
        score: float,
        threshold: float = 0.55
    ) -> bool:
        """Return whether the final answer lacks enough evidence to support a claim."""
        return self.should_recover(confidence_level, score, threshold)
    
    def get_recovery_ladder(
        self,
        current_compression_level: int
    ) -> List[int]:
        """
        Get the recovery ladder (progressively less aggressive compression).
        
        Args:
            current_compression_level: Current compression (0-4)
        
        Returns:
            List of compression levels to try, in order
        """
        ladder = []
        
        # Try progressively less aggressive levels
        for level in range(current_compression_level - 1, -1, -1):
            ladder.append(level)
        
        return ladder
    
    def generate_recovery_report(
        self,
        original_response: Dict,
        recovery_attempts: List[Dict]
    ) -> Dict:
        """
        Generate report on recovery process.
        
        Returns:
            Dictionary with recovery metrics and recommendations
        """
        return {
            "original_confidence": original_response.get('confidence'),
            "original_score": original_response.get('score'),
            "recovery_needed": len(recovery_attempts) > 0,
            "recovery_attempts": recovery_attempts,
            "final_confidence": recovery_attempts[-1]['confidence'] if recovery_attempts else original_response.get('confidence'),
            "final_score": recovery_attempts[-1]['score'] if recovery_attempts else original_response.get('score'),
            "compression_levels_tried": [a['compression_level'] for a in recovery_attempts],
            "success": len(recovery_attempts) > 0 and recovery_attempts[-1]['score'] >= 0.55,
            "recommendations": self._generate_recovery_recommendations(recovery_attempts)
        }
    
    def _generate_recovery_recommendations(self, recovery_attempts: List[Dict]) -> List[str]:
        """Generate recommendations based on recovery results"""
        recommendations = []
        
        if not recovery_attempts:
            recommendations.append("✓ No recovery needed - response quality acceptable")
        elif recovery_attempts[-1]['score'] >= 0.7:
            recommendations.append("✓ Recovery successful - restored confidence with expanded context")
        elif recovery_attempts[-1]['score'] >= 0.55:
            recommendations.append("⚠️ Recovery partially successful - acceptable but limited confidence")
        else:
            recommendations.append("❌ Recovery failed - consider using full context for this query type")
        
        # Check compression effectiveness
        compression_levels = [a['compression_level'] for a in recovery_attempts]
        if len(set(compression_levels)) > 2:
            recommendations.append(
                f"ℹ️ Required multiple rollback attempts - consider lower default compression for this domain"
            )
        
        return recommendations


# Example usage
if __name__ == "__main__":
    recovery = ContextRecovery()
    
    # Test evaluation
    test_query = "How do I solve a quadratic equation?"
    test_response = """
    To solve a quadratic equation ax² + bx + c = 0, you can use the quadratic formula:
    
    x = (-b ± √(b² - 4ac)) / 2a
    
    First, identify coefficients a, b, and c. Then, calculate the discriminant (b² - 4ac).
    Finally, apply the formula to get your two solutions.
    
    For example, x² - 5x + 6 = 0 has solutions x = 2 and x = 3.
    """
    test_context = "Quadratic equations are polynomial equations of degree 2..."
    
    confidence, score, metadata = recovery.evaluate_response_quality(
        test_query, test_response, test_context
    )
    
    print(f"Query: {test_query}")
    print(f"Confidence: {confidence.name}")
    print(f"Score: {score:.2f} (out of 1.0)")
    print(f"\nMetadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    
    print(f"\nNeeds Recovery: {recovery.should_recover(confidence, score)}")
