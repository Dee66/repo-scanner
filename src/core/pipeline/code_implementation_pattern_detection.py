"""Code Implementation Pattern Detection for Repository Intelligence Scanner.

This module analyzes the codebase to detect implementation patterns that support
or contradict documentation claims about features and capabilities.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class CodePatternDetector:
    """Detects implementation patterns in code that support documentation claims."""

    def __init__(self):
        self.patterns = {
            'security_patterns': {
                'authentication': [
                    r'auth|login|session|token|jwt|oauth',
                    r'password|credential|authenticate',
                    r'class.*Auth|def.*auth|function.*auth'
                ],
                'encryption': [
                    r'encrypt|decrypt|cipher|aes|rsa|ssl|tls',
                    r'cryptography|Crypto|Cipher',
                    r'hash|sha|md5|bcrypt'
                ],
                'authorization': [
                    r'authorize|permission|role|access|acl|rbac',
                    r'class.*Auth|def.*auth|function.*auth'
                ],
                'input_validation': [
                    r'validate|sanitize|escape|filter',
                    r'class.*Valid|def.*valid|function.*valid'
                ]
            },
            'architecture_patterns': {
                'microservices': [
                    r'microservice|service|api|endpoint',
                    r'docker|kubernetes|container',
                    r'rest|graphql|rpc'
                ],
                'database_patterns': [
                    r'database|db|sql|nosql|mongodb|postgres|mysql',
                    r'orm|model|entity|repository',
                    r'class.*Model|def.*db|function.*db'
                ],
                'web_frameworks': [
                    r'flask|django|fastapi|express|spring|rails',
                    r'class.*Controller|def.*route|function.*route'
                ],
                'testing_patterns': [
                    r'test|spec|unittest|pytest|junit|jest',
                    r'class.*Test|def.*test|function.*test',
                    r'mock|stub|fixture'
                ]
            },
            'language_patterns': {
                'python': [
                    r'def |class |import |from ',
                    r'__init__|__main__|__name__',
                    r'pip|requirements|setup\.py'
                ],
                'javascript': [
                    r'function |const |let |var ',
                    r'class |export |import ',
                    r'npm|package\.json|node'
                ],
                'java': [
                    r'public |private |class |interface ',
                    r'import |package ',
                    r'maven|gradle|pom\.xml'
                ]
            },
            'feature_patterns': {
                'api_endpoints': [
                    r'@app\.route|@router\.|app\.get|app\.post',
                    r'class.*API|def.*endpoint|function.*endpoint'
                ],
                'file_processing': [
                    r'open\(|read\(|write\(|close\(',
                    r'class.*File|def.*file|function.*file',
                    r'upload|download|stream'
                ],
                'data_processing': [
                    r'pandas|numpy|scipy|sklearn',
                    r'class.*Data|def.*process|function.*process',
                    r'map|filter|reduce|transform'
                ],
                'machine_learning': [
                    r'tensor|keras|pytorch|sklearn|ml',
                    r'class.*Model|def.*predict|function.*train',
                    r'neural|deep|learning|ai'
                ]
            }
        }

        self.file_type_patterns = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby'
        }

    def detect_implementation_patterns(self, file_list: List[str], semantic_analysis: Dict) -> Dict[str, Any]:
        """Detect implementation patterns that support documentation claims."""
        pattern_matches = {}
        file_patterns = {}

        # Analyze each file for patterns
        for file_path in file_list:
            if os.path.exists(file_path):
                file_patterns[file_path] = self._analyze_file_patterns(file_path)

        # Aggregate patterns by category
        for category, category_patterns in self.patterns.items():
            pattern_matches[category] = self._aggregate_category_patterns(file_patterns, category_patterns)

        # Detect architectural patterns
        architecture_detection = self._detect_architecture_patterns(file_patterns, semantic_analysis)

        # Detect feature implementations
        feature_detection = self._detect_feature_implementations(file_patterns, semantic_analysis)

        # Calculate pattern confidence scores
        pattern_confidence = self._calculate_pattern_confidence(pattern_matches, file_patterns)

        return {
            "file_patterns": file_patterns,
            "pattern_matches": pattern_matches,
            "architecture_detection": architecture_detection,
            "feature_detection": feature_detection,
            "pattern_confidence": pattern_confidence,
            "implementation_evidence": self._generate_implementation_evidence(pattern_matches, architecture_detection, feature_detection)
        }

    def _analyze_file_patterns(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file for implementation patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError):
            return {"error": "Could not read file"}

        file_extension = Path(file_path).suffix.lower()
        language = self.file_type_patterns.get(file_extension, 'unknown')

        patterns_found = {
            "language": language,
            "categories": {},
            "line_count": len(content.split('\n')),
            "character_count": len(content)
        }

        # Check each pattern category
        for category, category_patterns in self.patterns.items():
            category_matches = {}

            for pattern_name, patterns in category_patterns.items():
                matches = []
                for pattern in patterns:
                    try:
                        found = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                        if found:
                            matches.extend(found)
                    except re.error:
                        continue  # Skip invalid regex patterns

                if matches:
                    category_matches[pattern_name] = {
                        "matches": list(set(matches)),  # Remove duplicates
                        "count": len(matches),
                        "lines": self._find_matching_lines(content, patterns)
                    }

            if category_matches:
                patterns_found["categories"][category] = category_matches

        return patterns_found

    def _find_matching_lines(self, content: str, patterns: List[str]) -> List[int]:
        """Find line numbers where patterns match."""
        lines = content.split('\n')
        matching_lines = []

        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                try:
                    if re.search(pattern, line, re.IGNORECASE):
                        matching_lines.append(i)
                        break  # Only count each line once
                except re.error:
                    continue

        return matching_lines

    def _aggregate_category_patterns(self, file_patterns: Dict, category_patterns: Dict) -> Dict[str, Any]:
        """Aggregate patterns across all files for a category."""
        aggregated = {}

        for pattern_name, patterns in category_patterns.items():
            total_matches = []
            file_count = 0
            total_lines = []

            for file_path, file_data in file_patterns.items():
                if "categories" in file_data:
                    category_data = file_data["categories"].get("security_patterns", {})
                    pattern_data = category_data.get(pattern_name)

                    if pattern_data:
                        total_matches.extend(pattern_data["matches"])
                        file_count += 1
                        total_lines.extend(pattern_data["lines"])

            if file_count > 0:
                aggregated[pattern_name] = {
                    "total_matches": len(set(total_matches)),  # Unique matches
                    "files_with_pattern": file_count,
                    "total_files": len(file_patterns),
                    "coverage_percentage": (file_count / len(file_patterns)) * 100,
                    "sample_matches": list(set(total_matches))[:5]  # First 5 unique matches
                }

        return aggregated

    def _detect_architecture_patterns(self, file_patterns: Dict, semantic_analysis: Dict) -> Dict[str, Any]:
        """Detect architectural patterns from code analysis."""
        architecture = {
            "detected_patterns": [],
            "confidence_scores": {},
            "evidence": {}
        }

        # Check for microservices patterns
        microservice_indicators = self._count_pattern_matches(file_patterns, "architecture_patterns", "microservices")
        if microservice_indicators["files_with_pattern"] > 2:
            architecture["detected_patterns"].append("microservices")
            architecture["confidence_scores"]["microservices"] = min(1.0, microservice_indicators["files_with_pattern"] / 10)
            architecture["evidence"]["microservices"] = microservice_indicators

        # Check for web framework usage
        web_framework_indicators = self._count_pattern_matches(file_patterns, "architecture_patterns", "web_frameworks")
        if web_framework_indicators["files_with_pattern"] > 0:
            architecture["detected_patterns"].append("web_application")
            architecture["confidence_scores"]["web_application"] = min(1.0, web_framework_indicators["files_with_pattern"] / 5)
            architecture["evidence"]["web_application"] = web_framework_indicators

        # Check for database usage
        database_indicators = self._count_pattern_matches(file_patterns, "architecture_patterns", "database_patterns")
        if database_indicators["files_with_pattern"] > 0:
            architecture["detected_patterns"].append("database_application")
            architecture["confidence_scores"]["database_application"] = min(1.0, database_indicators["files_with_pattern"] / 3)
            architecture["evidence"]["database_application"] = database_indicators

        # Check for testing patterns
        testing_indicators = self._count_pattern_matches(file_patterns, "architecture_patterns", "testing_patterns")
        if testing_indicators["files_with_pattern"] > 0:
            architecture["detected_patterns"].append("tested_codebase")
            architecture["confidence_scores"]["tested_codebase"] = min(1.0, testing_indicators["files_with_pattern"] / len(file_patterns))
            architecture["evidence"]["tested_codebase"] = testing_indicators

        return architecture

    def _detect_feature_implementations(self, file_patterns: Dict, semantic_analysis: Dict) -> Dict[str, Any]:
        """Detect specific feature implementations."""
        features = {
            "implemented_features": [],
            "feature_confidence": {},
            "evidence": {}
        }

        # Check for API endpoints
        api_indicators = self._count_pattern_matches(file_patterns, "feature_patterns", "api_endpoints")
        if api_indicators["files_with_pattern"] > 0:
            features["implemented_features"].append("api_endpoints")
            features["feature_confidence"]["api_endpoints"] = min(1.0, api_indicators["files_with_pattern"] / 3)
            features["evidence"]["api_endpoints"] = api_indicators

        # Check for file processing
        file_indicators = self._count_pattern_matches(file_patterns, "feature_patterns", "file_processing")
        if file_indicators["files_with_pattern"] > 0:
            features["implemented_features"].append("file_processing")
            features["feature_confidence"]["file_processing"] = min(1.0, file_indicators["files_with_pattern"] / 2)
            features["evidence"]["file_processing"] = file_indicators

        # Check for data processing
        data_indicators = self._count_pattern_matches(file_patterns, "feature_patterns", "data_processing")
        if data_indicators["files_with_pattern"] > 0:
            features["implemented_features"].append("data_processing")
            features["feature_confidence"]["data_processing"] = min(1.0, data_indicators["files_with_pattern"] / 2)
            features["evidence"]["data_processing"] = data_indicators

        # Check for machine learning
        ml_indicators = self._count_pattern_matches(file_patterns, "feature_patterns", "machine_learning")
        if ml_indicators["files_with_pattern"] > 0:
            features["implemented_features"].append("machine_learning")
            features["feature_confidence"]["machine_learning"] = min(1.0, ml_indicators["files_with_pattern"] / 2)
            features["evidence"]["machine_learning"] = ml_indicators

        # Check for security features
        security_features = []
        for security_type in ["authentication", "encryption", "authorization", "input_validation"]:
            security_indicators = self._count_pattern_matches(file_patterns, "security_patterns", security_type)
            if security_indicators["files_with_pattern"] > 0:
                security_features.append(security_type)
                features["feature_confidence"][security_type] = min(1.0, security_indicators["files_with_pattern"] / 2)
                features["evidence"][security_type] = security_indicators

        if security_features:
            features["implemented_features"].append("security_features")
            features["feature_confidence"]["security_features"] = len(security_features) / 4  # Normalize by total security types

        return features

    def _count_pattern_matches(self, file_patterns: Dict, category: str, pattern_name: str) -> Dict[str, Any]:
        """Count matches for a specific pattern across all files."""
        total_matches = 0
        files_with_pattern = 0
        all_matches = []

        for file_path, file_data in file_patterns.items():
            if "categories" in file_data:
                category_data = file_data["categories"].get(category, {})
                pattern_data = category_data.get(pattern_name)

                if pattern_data:
                    total_matches += pattern_data["count"]
                    files_with_pattern += 1
                    all_matches.extend(pattern_data["matches"])

        return {
            "total_matches": total_matches,
            "files_with_pattern": files_with_pattern,
            "total_files": len(file_patterns),
            "coverage_percentage": (files_with_pattern / max(1, len(file_patterns))) * 100,
            "sample_matches": list(set(all_matches))[:5] if all_matches else []
        }

    def _calculate_pattern_confidence(self, pattern_matches: Dict, file_patterns: Dict) -> Dict[str, float]:
        """Calculate confidence scores for detected patterns."""
        confidence_scores = {}

        for category, category_data in pattern_matches.items():
            if category_data:
                # Calculate category confidence based on coverage and consistency
                total_files = len(file_patterns)
                category_files = sum(1 for file_data in file_patterns.values()
                                   if "categories" in file_data and category in file_data["categories"])

                confidence_scores[category] = min(1.0, category_files / max(1, total_files))

        return confidence_scores

    def _generate_implementation_evidence(self, pattern_matches: Dict, architecture: Dict, features: Dict) -> List[Dict[str, Any]]:
        """Generate evidence-based findings about implementation patterns."""
        evidence = []

        # Architecture evidence
        for pattern in architecture.get("detected_patterns", []):
            confidence = architecture.get("confidence_scores", {}).get(pattern, 0)
            evidence_data = architecture.get("evidence", {}).get(pattern, {})

            evidence.append({
                "type": "architecture",
                "pattern": pattern,
                "confidence": confidence,
                "evidence": f"Detected in {evidence_data.get('files_with_pattern', 0)} files",
                "description": f"Architectural pattern '{pattern}' detected with {confidence:.1%} confidence"
            })

        # Feature evidence
        for feature in features.get("implemented_features", []):
            confidence = features.get("feature_confidence", {}).get(feature, 0)
            evidence_data = features.get("evidence", {}).get(feature, {})

            evidence.append({
                "type": "feature",
                "feature": feature,
                "confidence": confidence,
                "evidence": f"Implemented in {evidence_data.get('files_with_pattern', 0)} files",
                "description": f"Feature '{feature}' implementation detected with {confidence:.1%} confidence"
            })

        # Pattern coverage evidence
        for category, category_data in pattern_matches.items():
            if category_data:
                total_patterns = len(category_data)
                high_coverage_patterns = sum(1 for p in category_data.values()
                                           if p.get("coverage_percentage", 0) > 50)

                if high_coverage_patterns > 0:
                    evidence.append({
                        "type": "pattern_coverage",
                        "category": category,
                        "confidence": high_coverage_patterns / total_patterns,
                        "evidence": f"{high_coverage_patterns}/{total_patterns} patterns have >50% file coverage",
                        "description": f"Category '{category}' has good implementation coverage"
                    })

        return evidence


def detect_code_implementation_patterns(file_list: List[str], semantic_analysis: Dict) -> Dict[str, Any]:
    """Main entry point for code implementation pattern detection."""
    detector = CodePatternDetector()
    return detector.detect_implementation_patterns(file_list, semantic_analysis)