"""Advanced Architectural Security Analysis for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
from enum import Enum

from ...exceptions import AnalysisError

class SecurityArchitecture(Enum):
    """Types of security architectures."""
    SANDBOXED_EXECUTION = "sandboxed_execution"
    ZERO_TRUST = "zero_trust"
    PREVENTION_FIRST = "prevention_first"
    DETERMINISTIC_SECURITY = "deterministic_security"
    OFFLINE_FIRST = "offline_first"
    CRYPTOGRAPHIC_BOUNDARY = "cryptographic_boundary"
    OPERATIONAL_ISOLATION = "operational_isolation"

@dataclass
class ArchitecturalFinding:
    """Represents an architectural security finding."""
    architecture_type: SecurityArchitecture
    confidence: float  # 0.0 to 1.0
    evidence: List[str]
    description: str
    file_path: str
    line_number: int
    code_snippet: str

class AdvancedArchitecturalAnalyzer:
    """Analyzes advanced architectural security patterns."""

    def __init__(self):
        self.findings: List[ArchitecturalFinding] = []
        self.architecture_patterns = self._load_architecture_patterns()

    def _load_architecture_patterns(self) -> Dict[SecurityArchitecture, Dict[str, Any]]:
        """Load patterns for detecting architectural security features."""
        return {
            SecurityArchitecture.SANDBOXED_EXECUTION: {
                'patterns': [
                    r'wasm|webassembly|emscripten',  # WASM execution
                    r'sandbox|isolate|container|jail',  # Sandboxing
                    r'execution.*limit|timeout.*\d+',  # Execution limits
                    r'memory.*limit|heap.*limit|stack.*limit',  # Memory limits
                    r'host.*import.*deny|syscall.*filter',  # Host isolation
                ],
                'evidence_weight': 0.8,
                'description': 'Sandboxed execution environment detected'
            },
            SecurityArchitecture.ZERO_TRUST: {
                'patterns': [
                    r'zero.*trust|never.*trust|assume.*breach',  # Zero trust principles
                    r'validate.*every|check.*every|verify.*every',  # Continuous validation
                    r'least.*privilege|minimal.*access',  # Least privilege
                    r'micro.*segmentation|network.*segment',  # Segmentation
                ],
                'evidence_weight': 0.7,
                'description': 'Zero trust architecture patterns detected'
            },
            SecurityArchitecture.PREVENTION_FIRST: {
                'patterns': [
                    r'prevent.*before|block.*before|stop.*before',  # Prevention focus
                    r'fail.*safe|safe.*fail|graceful.*fail',  # Fail-safe
                    r'credential.*scrub|env.*clean|data.*sanitize',  # Pre-cleaning
                    r'validate.*input.*before|check.*before.*execute',  # Pre-validation
                ],
                'evidence_weight': 0.9,
                'description': 'Prevention-first security approach detected'
            },
            SecurityArchitecture.DETERMINISTIC_SECURITY: {
                'patterns': [
                    r'deterministic|reproducible|consistent.*output',  # Deterministic behavior
                    r'audit.*trail|change.*detect|integrity.*verify',  # Auditability
                    r'version.*contract|semantic.*version|breaking.*change',  # Version contracts
                    r'hash.*verify|checksum.*validate',  # Integrity checks
                ],
                'evidence_weight': 0.6,
                'description': 'Deterministic security model detected'
            },
            SecurityArchitecture.OFFLINE_FIRST: {
                'patterns': [
                    r'offline.*first|local.*first|no.*network',  # Offline-first
                    r'cache.*first|store.*local|persistent.*local',  # Local storage
                    r'air.*gap|disconnect|isolate.*network',  # Network isolation
                    r'supply.*chain.*secure|dependency.*audit',  # Supply chain security
                ],
                'evidence_weight': 0.8,
                'description': 'Offline-first security design detected'
            },
            SecurityArchitecture.CRYPTOGRAPHIC_BOUNDARY: {
                'patterns': [
                    r'key.*generation.*build|compile.*key|embed.*key',  # Build-time keys
                    r'signature.*verify|integrity.*check|mac.*validate',  # Verification
                    r'encrypt.*memory|decrypt.*runtime|memory.*only',  # Runtime crypto
                    r'hmac|aes.*gcm|ed25519|rsa.*pss',  # Specific algorithms
                ],
                'evidence_weight': 0.7,
                'description': 'Cryptographic boundary protection detected'
            },
            SecurityArchitecture.OPERATIONAL_ISOLATION: {
                'patterns': [
                    r'diff.*only|pr.*only|change.*only',  # Operational boundaries
                    r'no.*live.*query|avoid.*infrastructure',  # Infrastructure isolation
                    r'plan.*only|spec.*only|declaration.*only',  # Declarative operations
                    r'boundary.*check|limit.*enforce|constraint.*apply',  # Boundary enforcement
                ],
                'evidence_weight': 0.6,
                'description': 'Operational isolation patterns detected'
            }
        }

    def analyze_architecture(self, file_list: List[str]) -> Dict[str, Any]:
        """Analyze files for advanced architectural security patterns."""
        self.findings = []

        for file_path in file_list:
            if self._is_code_file(file_path):
                self._analyze_file_architecture(file_path)

        # Aggregate findings by architecture type
        architecture_summary = self._summarize_architectures()

        return {
            'architectural_findings': [self._finding_to_dict(f) for f in self.findings],
            'architecture_summary': architecture_summary,
            'overall_architecture_score': self._calculate_overall_score(architecture_summary)
        }

    def _analyze_file_architecture(self, file_path: str):
        """Analyze a single file for architectural patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            for arch_type, pattern_data in self.architecture_patterns.items():
                self._check_architecture_patterns(content, lines, file_path, arch_type, pattern_data)

        except Exception as e:
            # Skip files that can't be analyzed
            pass

    def _check_architecture_patterns(self, content: str, lines: List[str], file_path: str,
                                   arch_type: SecurityArchitecture, pattern_data: Dict[str, Any]):
        """Check for specific architectural patterns."""
        evidence = []
        total_weight = 0

        for pattern in pattern_data['patterns']:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            if matches:
                # Find the best match (longest or most specific)
                best_match = max(matches, key=lambda m: len(m.group(0)))
                line_num = self._get_line_number(lines, best_match.start())

                if not self._is_in_test_or_comment(lines, line_num):
                    evidence.append({
                        'pattern': pattern,
                        'line': line_num,
                        'snippet': self._get_code_snippet(lines, line_num)
                    })
                    total_weight += pattern_data['evidence_weight']

        if evidence:
            # Calculate confidence based on evidence strength
            confidence = min(1.0, total_weight / len(pattern_data['patterns']))

            if confidence >= 0.5:  # Only report if confidence is reasonable
                finding = ArchitecturalFinding(
                    architecture_type=arch_type,
                    confidence=confidence,
                    evidence=[e['pattern'] for e in evidence],
                    description=pattern_data['description'],
                    file_path=file_path,
                    line_number=evidence[0]['line'],
                    code_snippet=evidence[0]['snippet']
                )
                self.findings.append(finding)

    def _summarize_architectures(self) -> Dict[str, Any]:
        """Summarize detected architectures."""
        summary = {}

        for arch in SecurityArchitecture:
            arch_findings = [f for f in self.findings if f.architecture_type == arch]
            if arch_findings:
                avg_confidence = sum(f.confidence for f in arch_findings) / len(arch_findings)
                summary[arch.value] = {
                    'detected': True,
                    'confidence': round(avg_confidence, 2),
                    'evidence_count': len(arch_findings),
                    'files': list(set(f.file_path for f in arch_findings))
                }
            else:
                summary[arch.value] = {
                    'detected': False,
                    'confidence': 0.0,
                    'evidence_count': 0,
                    'files': []
                }

        return summary

    def _calculate_overall_score(self, summary: Dict[str, Any]) -> float:
        """Calculate overall architectural security score."""
        detected_architectures = sum(1 for arch in summary.values() if arch['detected'])
        total_architectures = len(SecurityArchitecture)

        base_score = (detected_architectures / total_architectures) * 100

        # Weight by confidence
        confidence_weighted = sum(arch['confidence'] for arch in summary.values() if arch['detected'])
        confidence_bonus = min(20, confidence_weighted * 5)  # Up to 20 points bonus

        return round(min(100, base_score + confidence_bonus), 1)

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.py', '.rs', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rb', '.php'}
        return Path(file_path).suffix.lower() in code_extensions

    def _is_in_test_or_comment(self, lines: List[str], line_num: int) -> bool:
        """Check if finding is in test file or comment."""
        if line_num > 0 and line_num <= len(lines):
            line = lines[line_num - 1].strip()
            # Check for comments
            if line.startswith('#') or line.startswith('//') or '/*' in line:
                return True
        return False

    def _get_line_number(self, lines: List[str], char_pos: int) -> int:
        """Get line number from character position."""
        line_num = 1
        current_pos = 0
        for line in lines:
            current_pos += len(line) + 1
            if current_pos > char_pos:
                return line_num
            line_num += 1
        return line_num

    def _get_code_snippet(self, lines: List[str], line_num: int, context: int = 2) -> str:
        """Get code snippet around a line."""
        start = max(1, line_num - context)
        end = min(len(lines), line_num + context)
        snippet_lines = []
        for i in range(start, end + 1):
            marker = ">>> " if i == line_num else "    "
            snippet_lines.append(f"{marker}{i:4d}: {lines[i-1] if i <= len(lines) else ''}")
        return '\n'.join(snippet_lines)

    def _finding_to_dict(self, finding: ArchitecturalFinding) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            'architecture_type': finding.architecture_type.value,
            'confidence': finding.confidence,
            'evidence': finding.evidence,
            'description': finding.description,
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'code_snippet': finding.code_snippet
        }