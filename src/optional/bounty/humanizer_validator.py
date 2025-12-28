"""Humanizer Validator for Bounty PR Descriptions.

Validates and humanizes PR descriptions to avoid AI detection through:
- Perplexity analysis to ensure natural language patterns
- Anti-AI tone filters to replace generic phrases
- Entropy variation for sentence length diversity
- Jargon replacement for maintainer-specific terminology
"""

import re
import math
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)

@dataclass
class PerplexityScore:
    """Perplexity analysis results."""
    score: float
    is_human_like: bool
    recommendations: List[str]

@dataclass
class ToneAnalysis:
    """Tone analysis for AI detection avoidance."""
    ai_phrases_detected: List[str]
    humanized_suggestions: Dict[str, str]
    entropy_score: float
    overall_risk: str

class HumanizerValidator:
    """Validates and improves PR descriptions for human-like appearance."""

    def __init__(self):
        # AI detection patterns
        self.ai_phrases = {
            "implemented": ["added", "integrated", "built", "created"],
            "ensured": ["verified", "checked", "confirmed", "validated"],
            "improved": ["enhanced", "boosted", "upgraded", "refined"],
            "fixed": ["patched", "resolved", "corrected", "repaired"],
            "added": ["included", "incorporated", "inserted", "appended"],
            "removed": ["eliminated", "deleted", "stripped", "excluded"],
            "updated": ["modified", "changed", "revised", "adjusted"],
            "optimized": ["streamlined", "fine-tuned", "improved", "enhanced"],
            "refactored": ["restructured", "reorganized", "cleaned up", "simplified"],
            "integrated": ["connected", "linked", "merged", "combined"]
        }

        # Entropy thresholds
        self.min_entropy = 3.5  # Below this, text looks too uniform
        self.max_entropy = 6.5  # Above this, text looks too varied

        # Perplexity model (simplified n-gram based)
        self.ngram_model = self._build_ngram_model()

    def _build_ngram_model(self) -> Dict[str, Dict[str, float]]:
        """Build a simple n-gram model for perplexity calculation."""
        # This would be trained on human-written PR descriptions
        # For now, using a basic model
        return {
            "this": {"change": 0.3, "update": 0.2, "fix": 0.1},
            "the": {"code": 0.4, "function": 0.2, "issue": 0.1},
            "we": {"have": 0.5, "need": 0.3, "should": 0.2}
        }

    def analyze_perplexity(self, text: str) -> PerplexityScore:
        """Calculate perplexity score for text naturalness."""
        words = text.lower().split()
        if len(words) < 3:
            return PerplexityScore(0.0, False, ["Text too short for analysis"])

        perplexity = 0.0
        valid_ngrams = 0

        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i+1]}"
            next_word = words[i+2]

            if trigram in self.ngram_model:
                probs = self.ngram_model[trigram]
                if next_word in probs:
                    prob = probs[next_word]
                    perplexity += math.log2(prob)
                    valid_ngrams += 1

        if valid_ngrams == 0:
            return PerplexityScore(float('inf'), False, ["No recognizable patterns found"])

        avg_perplexity = -perplexity / valid_ngrams
        is_human_like = 2.0 <= avg_perplexity <= 8.0  # Human-like perplexity range

        recommendations = []
        if not is_human_like:
            if avg_perplexity < 2.0:
                recommendations.append("Text appears too predictable - vary sentence structure")
            else:
                recommendations.append("Text appears too random - use more common phrases")

        return PerplexityScore(avg_perplexity, is_human_like, recommendations)

    def analyze_tone(self, text: str) -> ToneAnalysis:
        """Analyze text for AI-like tone patterns."""
        words = re.findall(r'\b\w+\b', text.lower())
        ai_phrases_detected = []
        humanized_suggestions = {}

        # Check for AI phrases
        for ai_phrase, alternatives in self.ai_phrases.items():
            if ai_phrase in words:
                ai_phrases_detected.append(ai_phrase)
                humanized_suggestions[ai_phrase] = alternatives[0]  # Suggest first alternative

        # Calculate entropy (sentence length variation)
        sentences = re.split(r'[.!?]+', text)
        sentence_lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences if s.strip()]

        if sentence_lengths:
            entropy = self._calculate_entropy(sentence_lengths)
        else:
            entropy = 0.0

        # Determine risk level
        if entropy < self.min_entropy:
            overall_risk = "high"
        elif entropy > self.max_entropy:
            overall_risk = "medium"
        else:
            overall_risk = "low"

        return ToneAnalysis(
            ai_phrases_detected=ai_phrases_detected,
            humanized_suggestions=humanized_suggestions,
            entropy_score=entropy,
            overall_risk=overall_risk
        )

    def _calculate_entropy(self, lengths: List[int]) -> float:
        """Calculate Shannon entropy of sentence lengths."""
        if not lengths:
            return 0.0

        total = len(lengths)
        counts = Counter(lengths)
        entropy = 0.0

        for count in counts.values():
            prob = count / total
            entropy -= prob * math.log2(prob)

        return entropy

    def humanize_text(self, text: str, maintainer_profile: Optional[Dict] = None) -> str:
        """Apply humanization transformations to text."""
        humanized = text

        # Apply tone humanization
        tone_analysis = self.analyze_tone(text)
        for ai_phrase, suggestion in tone_analysis.humanized_suggestions.items():
            # Replace with some probability to avoid uniformity
            if hash(ai_phrase + text[:10]) % 3 == 0:  # 33% replacement rate
                humanized = re.sub(rf'\b{re.escape(ai_phrase)}\b', suggestion, humanized, flags=re.IGNORECASE)

        # Apply maintainer-specific jargon if profile provided
        if maintainer_profile:
            jargon_map = maintainer_profile.get('jargon_replacements', {})
            for old_term, new_term in jargon_map.items():
                humanized = re.sub(rf'\b{re.escape(old_term)}\b', new_term, humanized, flags=re.IGNORECASE)

        # Add entropy variation (slight sentence length adjustments)
        humanized = self._vary_sentence_lengths(humanized)

        return humanized

    def _vary_sentence_lengths(self, text: str) -> str:
        """Introduce slight variations in sentence lengths for natural flow."""
        sentences = re.split(r'([.!?]+)', text)
        varied_sentences = []

        for i, sentence in enumerate(sentences):
            if i % 2 == 0 and sentence.strip():  # Every other sentence
                # Add a transitional phrase occasionally
                if len(sentence.split()) > 10 and hash(sentence[:10]) % 5 == 0:
                    sentence = sentence.rstrip() + ", you know"
            varied_sentences.append(sentence)

        return ''.join(varied_sentences)

    def vibe_check_fail(self, description: str, maintainer_profile: Optional[Dict] = None,
                       threshold: float = 0.7) -> bool:
        """Check if the description fails the 'vibe check' for AI detection.

        Returns True if the description is likely to be flagged as AI-generated.
        This is a high-level check that combines multiple AI detection signals.
        """
        validation = self.validate_pr_description(description, maintainer_profile)

        # Multiple signals for AI detection failure
        signals = []

        # Perplexity check - too predictable or too random
        perplexity_score = validation.get("perplexity_score", 0)
        if not (2.0 <= perplexity_score <= 8.0):
            signals.append("perplexity_out_of_range")

        # Tone risk check
        tone_risk = validation.get("tone_risk", "low")
        if tone_risk == "high":
            signals.append("high_tone_risk")
        elif tone_risk == "medium":
            signals.append("medium_tone_risk")

        # AI phrases check
        ai_phrases = validation.get("ai_phrases_found", [])
        if len(ai_phrases) > 2:
            signals.append("excessive_ai_phrases")

        # Entropy check
        entropy_score = validation.get("entropy_score", 0)
        if entropy_score < self.min_entropy or entropy_score > self.max_entropy:
            signals.append("entropy_out_of_range")

        # Overall validation check
        if not validation.get("passes_validation", False):
            signals.append("validation_failed")

        # Calculate failure score based on signals
        failure_score = len(signals) / 6.0  # Normalize to 0-1 scale

        # Apply threshold
        return failure_score >= threshold

    def validate_pr_description(self, description: str, maintainer_profile: Optional[Dict] = None) -> Dict[str, Any]:
        """Complete validation of PR description."""
        perplexity = self.analyze_perplexity(description)
        tone = self.analyze_tone(description)

        # Overall assessment
        passes_validation = perplexity.is_human_like and tone.overall_risk != "high"

        humanized_version = self.humanize_text(description, maintainer_profile) if not passes_validation else description

        return {
            "passes_validation": passes_validation,
            "perplexity_score": perplexity.score,
            "tone_risk": tone.overall_risk,
            "ai_phrases_found": tone.ai_phrases_detected,
            "recommendations": perplexity.recommendations,
            "humanized_version": humanized_version,
            "entropy_score": tone.entropy_score
        }

# Convenience functions
def validate_pr_humanity(description: str, maintainer_profile: Optional[Dict] = None) -> Dict[str, Any]:
    """Convenience function for PR description validation."""
    validator = HumanizerValidator()
    return validator.validate_pr_description(description, maintainer_profile)

def humanize_pr_description(description: str, maintainer_profile: Optional[Dict] = None) -> str:
    """Convenience function for humanizing PR descriptions."""
    validator = HumanizerValidator()
    return validator.humanize_text(description, maintainer_profile)

def check_vibe_fail(description: str, maintainer_profile: Optional[Dict] = None,
                   threshold: float = 0.7) -> bool:
    """Convenience function for checking if description fails vibe check."""
    validator = HumanizerValidator()
def check_vibe_fail(description: str, maintainer_profile: Optional[Dict] = None,
                   threshold: float = 0.7) -> bool:
    """Convenience function for checking if description fails vibe check."""
    validator = HumanizerValidator()
    return validator.vibe_check_fail(description, maintainer_profile, threshold)
