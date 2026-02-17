import re
from typing import Dict
from enum import Enum


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MockInjectionClassifier:
    """Mock injection classifier using pattern matching.

    This will be replaced with a trained PyTorch model later.
    Interface is designed for easy swapping.
    """

    # Pattern definitions for injection detection
    SQL_PATTERNS = [
        r'(?i)\bSELECT\b.*\bFROM\b',
        r'(?i)\bUNION\b.*\bSELECT\b',
        r'(?i)\bINSERT\b.*\bINTO\b',
        r'(?i)\bUPDATE\b.*\bSET\b',
        r'(?i)\bDELETE\b.*\bFROM\b',
        r'(?i)\bDROP\b.*\bTABLE\b',
        r'(?i)\bOR\b\s+\d+\s*=\s*\d+',
        r'(?i)\bAND\b\s+\d+\s*=\s*\d+',
        r'--\s*$',
        r';\s*--',
    ]

    CODE_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'<\?php',
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'\bsystem\s*\(',
    ]

    OTHER_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'/etc/passwd',
        r'/etc/shadow',
        r'%00',
        r'\x00',
    ]

    def predict(self, http_request: str) -> Dict[str, any]:
        """Classify an HTTP request string.

        Args:
            http_request: The HTTP request string to classify

        Returns:
            Dictionary with keys:
            - class: "Normal" | "SQL Injection" | "Code Injection" | "Other Attacks"
            - confidence: float between 0.0 and 1.0
            - confidence_level: "LOW" | "MEDIUM" | "HIGH"
        """
        if not http_request or not http_request.strip():
            return {
                "class": "Normal",
                "confidence": 0.9,
                "confidence_level": ConfidenceLevel.HIGH.value
            }

        # Check each attack type and calculate confidence
        sql_score = self._match_patterns(http_request, self.SQL_PATTERNS)
        code_score = self._match_patterns(http_request, self.CODE_PATTERNS)
        other_score = self._match_patterns(http_request, self.OTHER_PATTERNS)

        # Determine prediction
        max_score = max(sql_score, code_score, other_score)

        # Lower threshold - any pattern match indicates potential attack
        if max_score < 0.09:
            return {
                "class": "Normal",
                "confidence": 1.0 - max_score,
                "confidence_level": self._get_confidence_level(1.0 - max_score).value
            }

        if sql_score == max_score:
            prediction_class = "SQL Injection"
        elif code_score == max_score:
            prediction_class = "Code Injection"
        else:
            prediction_class = "Other Attacks"

        # Scale confidence: higher pattern match ratio = higher confidence
        confidence = min(max_score * 1.5 + 0.4, 0.99)

        return {
            "class": prediction_class,
            "confidence": round(confidence, 2),
            "confidence_level": self._get_confidence_level(confidence).value
        }

    def _match_patterns(self, text: str, patterns: list) -> float:
        """Calculate match score for a list of patterns."""
        if not patterns:
            return 0.0
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        return matches / len(patterns)

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level."""
        if confidence < 0.5:
            return ConfidenceLevel.LOW
        elif confidence <= 0.8:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.HIGH
