"""
Malicious Intent Detection

Detects patterns indicating malicious repository intent including:
- Credential theft and exfiltration
- Data exfiltration
- Backdoors and hidden access
- Obfuscation techniques
- Cryptocurrency miners
- Command injection
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MaliciousPattern:
    """Represents a malicious code pattern."""
    pattern_id: str
    category: str
    severity: str
    confidence: float
    description: str
    evidence: str
    file_path: str
    line_number: int
    remediation: str
    impact: str


class MaliciousIntentDetector:
    """Detects malicious intent patterns in code."""
    
    def __init__(self):
        """Initialize detector with pattern definitions."""
        self.patterns = self._initialize_patterns()
        
    def _initialize_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize detection patterns."""
        return {
            'credential_theft': [
                {
                    'id': 'CRED_001',
                    'name': 'Environment Variable Exfiltration',
                    'regex': r'(requests|urllib|http)\.(post|put|get)\([^)]*(?:os\.environ|process\.env|getenv)',
                    'severity': 'critical',
                    'confidence': 0.90,
                    'description': 'Code attempts to send environment variables to external server',
                    'impact': 'Complete credential and secret compromise',
                    'remediation': 'Remove external transmission of environment variables'
                },
                {
                    'id': 'CRED_002',
                    'name': 'SSH Key Exfiltration',
                    'regex': r'(open|read|readFile)\([^)]*\.ssh/(id_rsa|id_ed25519|config)',
                    'severity': 'critical',
                    'confidence': 0.95,
                    'description': 'Code reads SSH private keys from standard locations',
                    'impact': 'Complete SSH access compromise',
                    'remediation': 'Remove SSH key access'
                },
                {
                    'id': 'CRED_003',
                    'name': 'AWS Credential Access',
                    'regex': r'(open|read|readFile)\([^)]*\.aws/credentials',
                    'severity': 'critical',
                    'confidence': 0.95,
                    'description': 'Code accesses AWS credentials file',
                    'impact': 'Complete AWS account compromise',
                    'remediation': 'Remove AWS credential file access'
                },
                {
                    'id': 'CRED_004',
                    'name': 'Git Credentials Access',
                    'regex': r'(open|read|readFile)\(["\'].*\.git-credentials',
                    'severity': 'high',
                    'confidence': 0.90,
                    'description': 'Code accesses Git credentials',
                    'impact': 'Git repository access compromise',
                    'remediation': 'Remove .git-credentials access'
                }
            ],
            'data_exfiltration': [
                {
                    'id': 'EXFIL_001',
                    'name': 'System File Upload',
                    'regex': r'(requests|urllib|http)\.(post|put)\([^)]*(?:/etc/passwd|/etc/shadow|/proc/)|with\s+open\s*\(\s*[\'\"](/etc/passwd|/etc/shadow|/proc/)',
                    'severity': 'critical',
                    'confidence': 0.92,
                    'description': 'Code uploads sensitive system files to external server',
                    'impact': 'System information disclosure',
                    'remediation': 'Remove external file transmission'
                },
                {
                    'id': 'EXFIL_002',
                    'name': 'Database Dump Exfiltration',
                    'regex': r'(mysqldump|pg_dump|mongodump)[^;]*\s*[|&]\s*(curl|wget|nc)',
                    'severity': 'critical',
                    'confidence': 0.88,
                    'description': 'Code dumps database and pipes to network tool',
                    'impact': 'Complete database compromise',
                    'remediation': 'Remove database dump piping'
                },
                {
                    'id': 'EXFIL_003',
                    'name': 'File System Scanning',
                    'regex': r'(os\.walk|glob|find)\([^)]*\).*?(requests|urllib|socket)\.(post|send)',
                    'severity': 'high',
                    'confidence': 0.75,
                    'description': 'Code scans filesystem and sends results externally',
                    'impact': 'File system disclosure',
                    'remediation': 'Remove filesystem scanning and transmission'
                }
            ],
            'backdoors': [
                {
                    'id': 'BACK_001',
                    'name': 'Hardcoded Admin Credentials',
                    'regex': r'(password|passwd|pwd)\s*==\s*["\'](?:admin123|password|123456|root)',
                    'severity': 'critical',
                    'confidence': 0.85,
                    'description': 'Hardcoded backdoor password in authentication logic',
                    'impact': 'Unauthorized administrative access',
                    'remediation': 'Remove hardcoded credentials'
                },
                {
                    'id': 'BACK_002',
                    'name': 'Hardcoded Backdoor User',
                    'regex': r'(user|username|login)\s*(?:==|in)\s*(?:["\'](?:backdoor|debug_admin|hidden_user)|[\[\(][^\]]*["\'](?:backdoor|debug_admin|hidden_user))',
                    'severity': 'critical',
                    'confidence': 0.88,
                    'description': 'Hardcoded backdoor username in authentication',
                    'impact': 'Unauthorized administrative access',
                    'remediation': 'Remove backdoor user account'
                },
                {
                    'id': 'BACK_003',
                    'name': 'Remote Shell Listener',
                    'regex': r'(socket|nc|netcat)\.(?:bind|listen)\(["\']0\.0\.0\.0["\']',
                    'severity': 'critical',
                    'confidence': 0.95,
                    'description': 'Code opens network listener on all interfaces',
                    'impact': 'Remote code execution backdoor',
                    'remediation': 'Remove network listener'
                },
                {
                    'id': 'BACK_004',
                    'name': 'Reverse Shell Connection',
                    'regex': r'(socket\.connect|subprocess\.Popen).*?(/bin/(ba)?sh|cmd\.exe)',
                    'severity': 'critical',
                    'confidence': 0.92,
                    'description': 'Code establishes reverse shell connection',
                    'impact': 'Remote code execution',
                    'remediation': 'Remove reverse shell code'
                }
            ],
            'obfuscation': [
                {
                    'id': 'OBFS_001',
                    'name': 'Base64 Decode + Exec',
                    'regex': r'(exec|eval)\(.*?base64\.(?:b64decode|decodebytes)',
                    'severity': 'high',
                    'confidence': 0.90,
                    'description': 'Code decodes base64 and executes result',
                    'impact': 'Hidden malicious code execution',
                    'remediation': 'Remove obfuscated code execution'
                },
                {
                    'id': 'OBFS_002',
                    'name': 'Hex Decode + Exec',
                    'regex': r'(exec|eval)\(.*?(?:unhexlify|fromhex|decode\(["\']hex)',
                    'severity': 'high',
                    'confidence': 0.88,
                    'description': 'Code decodes hex and executes result',
                    'impact': 'Hidden malicious code execution',
                    'remediation': 'Remove obfuscated code execution'
                },
                {
                    'id': 'OBFS_003',
                    'name': 'Dynamic Import Obfuscation',
                    'regex': r'__import__\(["\'].*?["\']\.decode\(',
                    'severity': 'medium',
                    'confidence': 0.75,
                    'description': 'Code dynamically imports decoded module names',
                    'impact': 'Hidden import obfuscation',
                    'remediation': 'Use clear import statements'
                },
                {
                    'id': 'OBFS_004',
                    'name': 'String Concatenation Obfuscation',
                    'regex': r'(exec|eval)\(["\'][a-zA-Z][\'"]\s*\+\s*["\'][a-zA-Z]',
                    'severity': 'medium',
                    'confidence': 0.70,
                    'description': 'Code uses string concatenation to hide execution',
                    'impact': 'Code obfuscation',
                    'remediation': 'Use clear code'
                }
            ],
            'cryptocurrency_mining': [
                {
                    'id': 'CRYPTO_001',
                    'name': 'Mining Pool Connection',
                    'regex': r'(\w+\.connect|requests\.post)\s*\([^\)]*(?:pool\.|mining|stratum)',
                    'severity': 'high',
                    'confidence': 0.85,
                    'description': 'Code connects to cryptocurrency mining pool',
                    'impact': 'Resource theft (CPU/GPU)',
                    'remediation': 'Remove mining code'
                },
                {
                    'id': 'CRYPTO_002',
                    'name': 'XMR/Monero Mining',
                    'regex': r'(xmrig|monero|randomx|cryptonight)',
                    'severity': 'high',
                    'confidence': 0.90,
                    'description': 'Code references Monero mining software',
                    'impact': 'Resource theft (CPU)',
                    'remediation': 'Remove mining software'
                },
                {
                    'id': 'CRYPTO_003',
                    'name': 'Mining Wallet Address',
                    'regex': r'["\'](?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{39,59})',
                    'severity': 'medium',
                    'confidence': 0.60,
                    'description': 'Possible cryptocurrency wallet address',
                    'impact': 'Potential mining configuration',
                    'remediation': 'Review wallet address usage'
                }
            ],
            'command_injection': [
                {
                    'id': 'CMD_001',
                    'name': 'Unsafe Shell Command',
                    'regex': r'(subprocess\.call|os\.system|subprocess\.run)\([^)]*shell\s*=\s*True',
                    'severity': 'high',
                    'confidence': 0.80,
                    'description': 'Code executes shell commands with shell=True',
                    'impact': 'Command injection vulnerability',
                    'remediation': 'Use shell=False and list arguments'
                },
                {
                    'id': 'CMD_002',
                    'name': 'User Input in Command',
                    'regex': r'(subprocess|os\.system).*?(?:input\(|request\.|argv\[|sys\.argv)',
                    'severity': 'critical',
                    'confidence': 0.85,
                    'description': 'User input passed to shell command',
                    'impact': 'Remote code execution',
                    'remediation': 'Sanitize input and use parameterized commands'
                },
                {
                    'id': 'CMD_003',
                    'name': 'Eval with User Input',
                    'regex': r'(eval|exec)\s*\(\s*(?:input\(|request\.|argv\[|user_\w+)',
                    'severity': 'critical',
                    'confidence': 0.95,
                    'description': 'User input passed to eval/exec',
                    'impact': 'Arbitrary code execution',
                    'remediation': 'Never use eval/exec with user input'
                }
            ]
        }
    
    def analyze_file(self, file_path: Path, content: str) -> List[MaliciousPattern]:
        """
        Analyze a file for malicious patterns.
        
        Args:
            file_path: Path to file being analyzed
            content: File content
            
        Returns:
            List of detected malicious patterns
        """
        detections = []
        lines = content.split('\n')
        
        for category, pattern_list in self.patterns.items():
            for pattern_def in pattern_list:
                matches = self._find_pattern_matches(
                    content, lines, pattern_def, category, str(file_path)
                )
                detections.extend(matches)
        
        return detections
    
    def _find_pattern_matches(self, content: str, lines: List[str], 
                             pattern_def: Dict[str, Any], category: str, 
                             file_path: str) -> List[MaliciousPattern]:
        """Find all matches of a pattern in content."""
        matches = []
        pattern = re.compile(pattern_def['regex'], re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        for match in pattern.finditer(content):
            # Find line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Get evidence (matched line with context)
            evidence_lines = []
            start_line = max(0, line_num - 2)
            end_line = min(len(lines), line_num + 2)
            for i in range(start_line, end_line):
                if i < len(lines):
                    prefix = '>' if i == line_num - 1 else ' '
                    evidence_lines.append(f"{prefix} {i+1:4d} | {lines[i]}")
            evidence = '\n'.join(evidence_lines)
            
            matches.append(MaliciousPattern(
                pattern_id=pattern_def['id'],
                category=category,
                severity=pattern_def['severity'],
                confidence=pattern_def['confidence'],
                description=pattern_def['description'],
                evidence=evidence,
                file_path=file_path,
                line_number=line_num,
                remediation=pattern_def['remediation'],
                impact=pattern_def['impact']
            ))
        
        return matches
    
    def generate_report(self, detections: List[MaliciousPattern]) -> Dict[str, Any]:
        """
        Generate comprehensive malicious intent report.
        
        Args:
            detections: List of detected patterns
            
        Returns:
            Report dictionary with analysis and recommendations
        """
        if not detections:
            return {
                'overall_risk': 'LOW',
                'risk_score': 1.0,
                'malicious_intent_detected': False,
                'summary': 'No malicious patterns detected',
                'detections': []
            }
        
        # Calculate overall risk
        critical_count = sum(1 for d in detections if d.severity == 'critical')
        high_count = sum(1 for d in detections if d.severity == 'high')
        
        if critical_count >= 3:
            overall_risk = 'CRITICAL'
            risk_score = 10.0
            summary = (f"SEVERE MALICIOUS INTENT DETECTED - {critical_count} critical patterns found. "
                      "This repository likely contains malicious code.")
        elif critical_count >= 1:
            overall_risk = 'HIGH'
            risk_score = 8.0 + critical_count
            summary = (f"Malicious patterns detected - {critical_count} critical, {high_count} high severity. "
                      "Manual review required before use.")
        elif high_count >= 3:
            overall_risk = 'MEDIUM'
            risk_score = 6.0 + high_count * 0.5
            summary = f"Suspicious patterns detected - {high_count} high severity findings require review."
        else:
            overall_risk = 'LOW'
            risk_score = 3.0 + len(detections) * 0.5
            summary = f"{len(detections)} suspicious pattern(s) detected - review recommended."
        
        # Group by category
        by_category: Dict[str, List[MaliciousPattern]] = {}
        for detection in detections:
            if detection.category not in by_category:
                by_category[detection.category] = []
            by_category[detection.category].append(detection)
        
        # Top 5 most critical detections
        sorted_detections = sorted(
            detections,
            key=lambda d: (
                {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(d.severity, 0),
                d.confidence
            ),
            reverse=True
        )
        
        top_threats = []
        for detection in sorted_detections[:5]:
            top_threats.append({
                'pattern_id': detection.pattern_id,
                'category': detection.category.replace('_', ' ').title(),
                'severity': detection.severity.upper(),
                'confidence': f"{detection.confidence:.0%}",
                'description': detection.description,
                'impact': detection.impact,
                'location': f"{detection.file_path}:{detection.line_number}",
                'remediation': detection.remediation
            })
        
        return {
            'overall_risk': overall_risk,
            'risk_score': min(10.0, risk_score),
            'malicious_intent_detected': critical_count >= 1 or high_count >= 2,
            'summary': summary,
            'total_detections': len(detections),
            'by_severity': {
                'critical': critical_count,
                'high': high_count,
                'medium': sum(1 for d in detections if d.severity == 'medium'),
                'low': sum(1 for d in detections if d.severity == 'low')
            },
            'by_category': {cat: len(dets) for cat, dets in by_category.items()},
            'top_threats': top_threats,
            'all_detections': [
                {
                    'pattern_id': d.pattern_id,
                    'category': d.category,
                    'severity': d.severity,
                    'confidence': d.confidence,
                    'description': d.description,
                    'file_path': d.file_path,
                    'line_number': d.line_number,
                    'evidence': d.evidence,
                    'impact': d.impact,
                    'remediation': d.remediation
                }
                for d in detections
            ]
        }


def analyze_malicious_intent(repository_files: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze repository for malicious intent.
    
    Args:
        repository_files: Dict mapping file paths to content
        
    Returns:
        Malicious intent analysis report
    """
    detector = MaliciousIntentDetector()
    all_detections = []
    
    for file_path, content in repository_files.items():
        try:
            detections = detector.analyze_file(Path(file_path), content)
            all_detections.extend(detections)
        except Exception as e:
            logger.warning("Error analyzing %s: %s", file_path, e)
            continue
    
    return detector.generate_report(all_detections)
