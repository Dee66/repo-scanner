"""Security vulnerability analysis stage for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass

from .cryptographic_analysis import CryptographicAnalyzer
from .compliance_frameworks import ComplianceAnalyzer
from .architectural_security import AdvancedArchitecturalAnalyzer
from .confidence_scorer import ConfidenceScorer

# Import adapter manager for AST-based analysis
try:
    from adapters.language_adapter_manager import LanguageAdapterManager
except ImportError:
    LanguageAdapterManager = None

@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding."""
    vulnerability_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    cwe_id: str = ""  # Common Weakness Enumeration ID
    owasp_category: str = ""  # OWASP Top 10 category

class SecurityAnalyzer:
    """Analyzes code for security vulnerabilities using context-aware static analysis."""

    def __init__(self):
        # Common vulnerability patterns with improved context awareness
        self.vulnerability_patterns = {
            'sql_injection': {
                'patterns': [
                    r'\.execute\s*\(\s*["\']?\s*SELECT.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*INSERT.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*UPDATE.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*DELETE.*%s.*["\']?\s*\)',
                    r'cursor\.execute\s*\(\s*.*\+.*\)',
                    r'query\s*=.*%.*\s*db\.execute',
                ],
                'severity': 'high',
                'description': 'Potential SQL injection vulnerability',
                'cwe_id': 'CWE-89',
                'owasp_category': 'A03:2021-Injection',
                'skip_test_files': True
            },
            'xss_vulnerability': {
                'patterns': [
                    r'innerHTML\s*=.*\+',
                    r'document\.write\s*\(.*\+.*\)',
                    r'eval\s*\(.*\+.*\)',
                    r'setTimeout\s*\(.*\+.*\)',
                    r'setInterval\s*\(.*\+.*\)',
                ],
                'severity': 'high',
                'description': 'Potential Cross-Site Scripting (XSS) vulnerability',
                'cwe_id': 'CWE-79',
                'owasp_category': 'A03:2021-Injection',
                'skip_test_files': True
            },
            'weak_crypto': {
                'patterns': [
                    r'\bimport\s+md5\b',
                    r'\bfrom\s+crypt\s+import\b',
                    r'\bhashlib\.md5\s*\(',
                    r'\bhashlib\.sha1\s*\(',
                    r'\bMD5\s*\(',
                    r'\bSHA1\s*\(',
                    r'\bdes\s*\(',
                    r'\brc4\s*\(',
                ],
                'severity': 'medium',
                'description': 'Potentially weak cryptographic implementation',
                'cwe_id': 'CWE-327',
                'owasp_category': 'A02:2021-Cryptographic Failures',
                'skip_test_files': False,
                'safe_patterns': [
                    r'\brandom\.',  # random module is for non-crypto randomness
                    r'\bos\.urandom',  # urandom is secure for crypto
                    r'\bsecrets\.',  # secrets module is secure
                    r'\bcryptography\.',  # cryptography library is modern
                    r'\bbcrypt\.',  # bcrypt is secure
                    r'\bscrypt\.',  # scrypt is secure
                    r'\bargparse\.SHA1',  # argparse uses SHA1 for non-crypto purposes
                ]
            },
            'hardcoded_secrets': {
                'patterns': [
                    r'password\s*=\s*["\'][^"\']+["\']',
                    r'secret\s*=\s*["\'][^"\']+["\']',
                    r'key\s*=\s*["\'][^"\']+["\']',
                    r'token\s*=\s*["\'][^"\']+["\']',
                    r'api_key\s*=\s*["\'][^"\']+["\']',
                ],
                'severity': 'high',
                'description': 'Potential hardcoded secrets or credentials',
                'cwe_id': 'CWE-798',
                'owasp_category': 'A05:2021-Security Misconfiguration',
                'skip_test_files': True,  # Test files often have dummy credentials
                'skip_comments': True
            },
            'path_traversal': {
                'patterns': [
                    r'open\s*\(\s*.*\+\s*.*\)',  # open() with string concatenation
                    r'Path\s*\(\s*.*\+\s*.*\)',  # Path() with string concatenation
                    r'os\.path\.join\s*\(\s*.*\.\..*',  # os.path.join with .. in args
                    r'file\s*=\s*open\s*\(.*\+\s*.*\)',  # file=open() with concatenation
                    r'with\s+open\s*\(.*\+\s*.*\)',  # with open() with concatenation
                ],
                'severity': 'high',
                'description': 'Potential path traversal vulnerability',
                'cwe_id': 'CWE-22',
                'owasp_category': 'A01:2021-Broken Access Control',
                'skip_test_files': True,
                'context_check': True  # Requires additional validation
            },
            'command_injection': {
                'patterns': [
                    r'os\.system\s*\(.*\+.*\)',
                    r'subprocess\.call\s*\(.*\+.*\)',
                    r'os\.popen\s*\(.*\+.*\)',
                    r'subprocess\.Popen\s*\(.*\+.*\)',
                ],
                'severity': 'critical',
                'description': 'Potential command injection vulnerability',
                'cwe_id': 'CWE-78',
                'owasp_category': 'A03:2021-Injection',
                'skip_test_files': True
            },
            'insecure_deserialization': {
                'patterns': [
                    r'pickle\.loads?\s*\(',
                    r'yaml\.load\s*\(',
                    r'eval\s*\(',
                ],
                'severity': 'high',
                'description': 'Potential insecure deserialization',
                'cwe_id': 'CWE-502',
                'owasp_category': 'A08:2021-Software and Data Integrity Failures',
                'skip_test_files': True,
                'safe_patterns': [
                    r'json\.loads?\s*\(\s*sys\.stdin',  # CLI input parsing
                    r'json\.loads?\s*\(\s*response\.text',  # HTTP response parsing (may be safe)
                    r'json\.loads?\s*\(\s*open\s*\(',  # File reading (may be safe)
                ]
            },
            'weak_authentication': {
                'patterns': [
                    r'if\s+password\s*==\s*["\'][^"\']+["\']',  # Hardcoded password check
                    r'authenticate\s*\(\s*username.*password.*\)',  # Basic auth without proper validation
                    r'login\s*=\s*True',  # Automatic login
                ],
                'severity': 'high',
                'description': 'Weak or missing authentication mechanisms',
                'cwe_id': 'CWE-287',
                'owasp_category': 'A07:2021-Identification and Authentication Failures',
                'skip_test_files': True,
                'skip_comments': True
            },
            'missing_authorization': {
                'patterns': [
                    r'if\s+user\s*==\s*["\']admin["\']',  # Role-based check without proper authorization
                    r'access\s*=\s*True',  # Automatic access grant
                    r'admin\s*=\s*True',  # Hardcoded admin privileges
                ],
                'severity': 'high',
                'description': 'Missing or insufficient authorization checks',
                'cwe_id': 'CWE-862',
                'owasp_category': 'A01:2021-Broken Access Control',
                'skip_test_files': True,
                'skip_comments': True
            },
            'insecure_data_handling': {
                'patterns': [
                    r'print\s*\(\s*.*password.*\)',  # Logging passwords
                    r'log\..*\(\s*.*secret.*\)',  # Logging secrets
                    r'store\s*\(\s*.*(?:key|password|secret).*',  # Storing sensitive data insecurely
                ],
                'severity': 'medium',
                'description': 'Insecure handling of sensitive data',
                'cwe_id': 'CWE-200',
                'owasp_category': 'A02:2021-Cryptographic Failures',
                'skip_test_files': True,
                'skip_comments': True,
                'safe_patterns': [
                    r'bcrypt\.',  # Secure password hashing
                    r'hashlib\.',  # Secure hashing
                    r'cryptography\.',  # Secure crypto library
                ]
            },
            'trust_boundary_violation': {
                'patterns': [
                    r'untrusted\s*=.*input',  # Direct use of untrusted input
                    r'data\s*=.*request\.',  # Direct use of request data
                    r'user_input\s*=.*get',  # Direct use of user input
                ],
                'severity': 'medium',
                'description': 'Potential trust boundary violations',
                'cwe_id': 'CWE-501',
                'owasp_category': 'A08:2021-Software and Data Integrity Failures',
                'skip_test_files': True,
                'skip_comments': True
            },
            'sandboxing_mechanisms': {
                'patterns': [
                    r'wasm|webassembly',  # WebAssembly usage
                    r'sandbox|isolate|container',  # Sandboxing terms
                    r'execution.*limit|timeout.*ms',  # Execution limits
                    r'memory.*limit|heap.*limit',  # Memory limits
                ],
                'severity': 'info',
                'description': 'Potential sandboxing or isolation mechanisms detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'prevention_first_security': {
                'patterns': [
                    r'validate.*before|check.*before',  # Pre-validation
                    r'credential.*scrub|env.*clean',  # Credential scrubbing
                    r'fail.*safe|graceful.*degradation',  # Fail-safe mechanisms
                ],
                'severity': 'info',
                'description': 'Prevention-first security patterns detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'deterministic_security': {
                'patterns': [
                    r'deterministic|reproducible',  # Deterministic terms
                    r'audit.*trail|change.*detection',  # Auditability
                    r'version.*contract|semantic.*version',  # Version contracts
                ],
                'severity': 'info',
                'description': 'Deterministic security properties detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'offline_security': {
                'patterns': [
                    r'offline.*first|zero.*network',  # Offline-first
                    r'no.*internet|local.*only',  # Network isolation
                    r'supply.*chain.*secure',  # Supply chain security
                ],
                'severity': 'info',
                'description': 'Offline/network-isolated security design detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'cryptographic_lifecycle': {
                'patterns': [
                    r'key.*generation|key.*embedding',  # Key lifecycle
                    r'build.*time.*crypto|compile.*key',  # Build-time crypto
                    r'signature.*verify|integrity.*check',  # Verification
                ],
                'severity': 'info',
                'description': 'Cryptographic lifecycle management detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'multi_layer_validation': {
                'patterns': [
                    r'input.*sanitize|validate.*input',  # Input validation
                    r'depth.*limit|size.*limit',  # Limits
                    r'injection.*prevent|traversal.*block',  # Prevention
                ],
                'severity': 'info',
                'description': 'Multi-layer input validation detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'operational_boundaries': {
                'patterns': [
                    r'diff.*only|pr.*boundary',  # Operational boundaries
                    r'live.*infrastructure.*avoid',  # Infrastructure isolation
                    r'operational.*security',  # Operational security
                ],
                'severity': 'info',
                'description': 'Operational security boundaries detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'zero_network_enforcement': {
                'patterns': [
                    r'network.*check|no.*network|offline.*only',  # Network enforcement
                    r'credential.*scrub|env.*clean|aws.*credential.*check',  # Credential scrubbing
                    r'proxy.*detect|live.*deployment.*block',  # Environment validation
                    r'zero.*telemetry|no.*analytics|no.*tracking',  # Telemetry prevention
                ],
                'severity': 'info',
                'description': 'Zero-network enforcement and offline-first design detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'prevention_first_validation': {
                'patterns': [
                    r'pre.*command.*validation|before.*operation.*check',  # Pre-validation
                    r'fail.*safe|graceful.*fail|conservative.*block',  # Fail-safe mechanisms
                    r'input.*sanitize.*before|validate.*before.*process',  # Pre-sanitization
                    r'safety.*first|prevent.*before.*allow',  # Prevention-first approach
                ],
                'severity': 'info',
                'description': 'Prevention-first security validation detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'cryptographic_boundary': {
                'patterns': [
                    r'build.*time.*crypto|compile.*key|embedded.*key',  # Build-time crypto
                    r'runtime.*crypto.*isolate|memory.*only.*crypto',  # Runtime isolation
                    r'key.*generation.*build|signature.*verify.*runtime',  # Key lifecycle
                    r'cryptographic.*boundary|crypto.*enclave',  # Boundary protection
                ],
                'severity': 'info',
                'description': 'Cryptographic boundary protection and lifecycle management detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'multi_layer_input_validation': {
                'patterns': [
                    r'input.*sanitize.*multiple|validation.*layers',  # Multi-layer validation
                    r'depth.*limit.*\d+|size.*limit.*\d+',  # Depth/size limits
                    r'path.*traversal.*prevent|command.*injection.*block',  # Injection prevention
                    r'malformed.*input.*handle|graceful.*failure.*invalid',  # Error handling
                ],
                'severity': 'info',
                'description': 'Multi-layer input validation and sanitization detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            },
            'deterministic_security_model': {
                'patterns': [
                    r'deterministic.*output|reproducible.*result',  # Deterministic behavior
                    r'audit.*trail.*verify|change.*detect.*automated',  # Audit verification
                    r'hash.*stable.*output|consistent.*across.*environment',  # Consistency
                    r'security.*analysis.*trustworthy|automated.*assessment.*reliable',  # Trustworthy analysis
                ],
                'severity': 'info',
                'description': 'Deterministic security model with audit trail verification detected',
                'cwe_id': '',
                'owasp_category': 'Architectural Security',
                'skip_test_files': False,
                'skip_comments': True
            }
        }

        # Initialize adapter manager for AST-based analysis
        self.adapter_manager = LanguageAdapterManager() if LanguageAdapterManager else None

    def analyze_security_vulnerabilities(self, file_list: List[str], semantic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze files for security vulnerabilities.

        Args:
            file_list: List of file paths to analyze
            semantic: Semantic analysis results

        Returns:
            Dict containing security analysis results
        """
        findings = []
        analyzed_files = 0
        total_lines = 0

        for file_path in file_list:
            if self._should_analyze_file(file_path):
                file_findings = self._analyze_file(file_path)
                findings.extend(file_findings)
                analyzed_files += 1

                # Count lines for metrics
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += len(f.readlines())
                except Exception:
                    pass

        # Add cryptographic analysis
        # Temporarily disabled due to false positives
        # crypto_analyzer = CryptographicAnalyzer()
        # crypto_findings = crypto_analyzer.analyze_key_management(file_list)
        # Convert CryptoFinding to SecurityFinding
        # for cf in crypto_findings:
        #     findings.append(SecurityFinding(
        #         vulnerability_type=cf.finding_type,
        #         severity=cf.severity,
        #         file_path=cf.file_path,
        #         line_number=cf.line_number,
        #         description=cf.description,
        #         code_snippet=cf.code_snippet,
        #         cwe_id=cf.cwe_id,
        #         owasp_category='A02:2021-Cryptographic Failures'  # Default for crypto
        #     ))

        # Add compliance analysis
        # Temporarily disabled due to false positives
        # compliance_analyzer = ComplianceAnalyzer()
        # compliance_results = compliance_analyzer.analyze_compliance(file_list)
        # Convert ComplianceFinding to SecurityFinding
        # for framework, comp_findings in compliance_results.items():
        #     for cf in comp_findings:
        #         findings.append(SecurityFinding(
        #             vulnerability_type=f'{framework}_compliance',
        #             severity=cf.severity,
        #             file_path=cf.file_path,
        #             line_number=cf.line_number,
        #             description=f'{framework} {cf.requirement}: {cf.description}',
        #             code_snippet=cf.code_snippet,
        #             cwe_id='',  # Compliance doesn't use CWE
        #             owasp_category='Compliance'  # Custom category
        #         ))

        # Calculate risk scores
        risk_score = self._calculate_risk_score(findings, analyzed_files, total_lines)

        # Transform findings into the expected structure
        # Get language counts from actual analyzed files
        analyzed_languages = set()
        for finding in findings:
            lang = finding.file_path.split('.')[-1] if '.' in finding.file_path else 'unknown'
            analyzed_languages.add(lang)
        
        unsafe_patterns = {
            "summary": {
                "total_patterns": len(findings),
                "high_severity": len([f for f in findings if f.severity == 'high']),
                "medium_severity": len([f for f in findings if f.severity == 'medium']),
                "low_severity": len([f for f in findings if f.severity == 'low']),
                "languages_covered": len(analyzed_languages)
            },
            "patterns_by_language": {},
            "critical_findings": []
        }

        # Group findings by language
        from collections import defaultdict
        patterns_by_lang = defaultdict(list)
        for finding in findings:
            lang = finding.file_path.split('.')[-1] if '.' in finding.file_path else 'unknown'
            if lang not in unsafe_patterns["patterns_by_language"]:
                unsafe_patterns["patterns_by_language"][lang] = []
            unsafe_patterns["patterns_by_language"][lang].append({
                "file_path": finding.file_path,
                "language": lang,
                "patterns": [{
                    "type": finding.vulnerability_type,
                    "severity": finding.severity,
                    "description": finding.description,
                    "line": finding.line_number,
                    "code_snippet": finding.code_snippet
                }]
            })

            # Add high severity findings to critical findings
            if finding.severity == 'high':
                unsafe_patterns["critical_findings"].append({
                    "file_path": finding.file_path,
                    "pattern_type": finding.vulnerability_type,
                    "severity": finding.severity,
                    "description": finding.description,
                    "line": finding.line_number
                })

        # Sort critical findings
        unsafe_patterns["critical_findings"].sort(key=lambda x: x["file_path"])

        # Add advanced architectural analysis
        arch_analyzer = AdvancedArchitecturalAnalyzer()
        architectural_results = arch_analyzer.analyze_architecture(file_list)

        # Add confidence scoring and validation
        confidence_scorer = ConfidenceScorer()
        all_findings_dict = [self._finding_to_dict(f) for f in findings]
        validated_findings = confidence_scorer.validate_findings(all_findings_dict, file_list, semantic)
        confidence_report = confidence_scorer.generate_confidence_report(validated_findings)

        return {
            "unsafe_patterns": unsafe_patterns,
            "security_posture": risk_score,
            "recommendations": self._generate_security_recommendations(findings),
            "security_architecture_score": self._calculate_security_architecture_score(findings, analyzed_files, architectural_results),
            "compliance_readiness_matrix": self._generate_compliance_matrix(findings),
            "threat_model_coverage": self._assess_threat_model_coverage(findings),
            "advanced_architecture_analysis": architectural_results,
            "confidence_validation": {
                "overall_confidence": confidence_report.get("overall_confidence", 0),
                "total_validated_findings": confidence_report.get("total_validated_findings", 0),
                "confidence_distribution": confidence_report.get("confidence_distribution", {}),
                "average_false_positive_probability": confidence_report.get("average_false_positive_probability", 0),
                "evidence_strength_distribution": confidence_report.get("evidence_strength_distribution", {}),
                "reliability_assessment": confidence_report.get("reliability_assessment", "unknown"),
                "validated_findings": [self._validated_finding_to_dict(f) for f in validated_findings[:10]]  # Top 10 for brevity
            }
        }

    def _should_analyze_file(self, file_path: str) -> bool:
        """Determine if a file should be analyzed for security issues."""
        # Skip binary files, images, etc.
        skip_extensions = {'.jpg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.pyc', '.class'}

        if any(file_path.endswith(ext) for ext in skip_extensions):
            return False

        # Only analyze text files that are likely to contain code
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.php', '.rb', '.go', '.rs'}
        return any(file_path.endswith(ext) for ext in code_extensions)

    def _analyze_file(self, file_path: str) -> List[SecurityFinding]:
        """Analyze a single file for security vulnerabilities with context awareness."""
        findings = []

        # Check if this is a test file that should be handled differently
        is_test_file = self._is_test_file(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                # Skip comments and docstrings for certain patterns
                is_comment = self._is_comment_or_docstring(line, file_path)

                for vuln_type, vuln_config in self.vulnerability_patterns.items():
                    # Skip test files if configured
                    if vuln_config.get('skip_test_files', False) and is_test_file:
                        continue

                    # Skip comments if configured
                    if vuln_config.get('skip_comments', False) and is_comment:
                        continue

                    # Check if line matches any pattern
                    for pattern in vuln_config['patterns']:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Additional context checking for certain patterns
                            if vuln_config.get('context_check', False):
                                if not self._validate_context(line, vuln_type, content, line_num):
                                    continue

                            # Check for safe patterns that override the vulnerability
                            safe_patterns = vuln_config.get('safe_patterns', [])
                            is_safe = any(re.search(safe, line, re.IGNORECASE) for safe in safe_patterns)
                            if is_safe:
                                continue

                            finding = SecurityFinding(
                                vulnerability_type=vuln_type,
                                severity=vuln_config['severity'],
                                file_path=file_path,
                                line_number=line_num,
                                description=vuln_config['description'],
                                code_snippet=line.strip(),
                                cwe_id=vuln_config.get('cwe_id', ''),
                                owasp_category=vuln_config.get('owasp_category', '')
                            )
                            findings.append(finding)
                            break  # Only report one finding per line per type

            # Add AST-based analysis using adapters
            if self.adapter_manager:
                try:
                    adapter = self.adapter_manager.get_adapter_for_file(file_path)
                    if adapter:
                        print(f"DEBUG: Using adapter {adapter.__class__.__name__} for {file_path}")
                        ast_result = adapter.extract_ast(file_path)
                        unsafe_patterns = ast_result.get("unsafe_patterns", [])
                        print(f"DEBUG: ast_result keys: {list(ast_result.keys())}")
                        print(f"DEBUG: Found {len(unsafe_patterns)} unsafe patterns in {file_path}")
                        for pattern in unsafe_patterns:
                            print(f"DEBUG: Pattern: {pattern}")
                            severity_map = {"high": "high", "medium": "medium", "low": "low"}
                            finding = SecurityFinding(
                                vulnerability_type=pattern.get("type", "unknown"),
                                severity=severity_map.get(pattern.get("severity", "low"), "low"),
                                file_path=file_path,
                                line_number=pattern.get("line", 0),
                                description=pattern.get("description", "Unsafe pattern detected"),
                                code_snippet=pattern.get("code", ""),
                                cwe_id="",  # Could map types to CWE IDs
                                owasp_category=""
                            )
                            findings.append(finding)
                    else:
                        print(f"DEBUG: No adapter found for {file_path}")
                except Exception as e:
                    # Log error but continue
                    print(f"Error in AST analysis for {file_path}: {e}")

        except Exception as e:
            # Log error but continue analysis
            print(f"Error analyzing {file_path}: {e}")

        return findings

    def _is_test_file(self, file_path: str) -> bool:
        """Determine if a file is a test file."""
        path_lower = file_path.lower()
        return any(test_indicator in path_lower for test_indicator in [
            'test', 'spec', 'fixture', 'mock', 'stub'
        ])

    def _is_comment_or_docstring(self, line: str, file_path: str) -> bool:
        """Check if a line is a comment or docstring."""
        stripped = line.strip()

        # Check for language-specific comment markers
        if file_path.endswith(('.py', '.rs', '.java', '.cpp', '.c', '.php', '.go')):
            if stripped.startswith('#'):
                return True
            # Python docstrings
            if '"""' in line or "'''" in line:
                return True
        elif file_path.endswith(('.js', '.ts', '.java')):
            if stripped.startswith('//') or stripped.startswith('/*'):
                return True
        elif file_path.endswith(('.rb',)):
            if stripped.startswith('#'):
                return True

        return False

    def _validate_context(self, line: str, vuln_type: str, content: str, line_num: int) -> bool:
        """Perform additional context validation for certain vulnerability types."""
        if vuln_type == 'path_traversal':
            # For path traversal, check if this looks like a security test or safe operation
            context_lines = self._get_context_lines(content, line_num, 5)
            context_text = '\n'.join(context_lines).lower()

            # If this appears to be testing path traversal prevention, skip it
            security_indicators = [
                'assert', 'should_fail', 'forbidden', 'blocked', 'prevent',
                'security', 'test_path_traversal', 'exploit'
            ]

            if any(indicator in context_text for indicator in security_indicators):
                return False

            # Check if the path construction looks dangerous
            # Skip if it uses safe path operations
            safe_indicators = [
                'os.path.join', 'pathlib.path', 'path.join',
                'require(', 'import ', 'from ',  # Safe relative imports
                'template', 'format', 'string',  # String formatting/template operations
            ]

            if any(indicator in context_text for indicator in safe_indicators):
                return False

            # Skip if it's clearly a string literal (not a variable operation)
            stripped = line.strip()
            if stripped.startswith('"') or stripped.startswith("'") or '"""' in stripped or "'''" in stripped:
                return False

            # Only flag if it looks like actual file system operations with user input
            dangerous_indicators = [
                'user_input', 'request.', 'input', 'argv', 'parameter',
                'filename', 'filepath', 'dirname'
            ]

            return any(indicator in context_text for indicator in dangerous_indicators)

        return True

    def _get_context_lines(self, content: str, line_num: int, context_size: int = 3) -> List[str]:
        """Get lines around a specific line number for context."""
        lines = content.splitlines()
        start = max(0, line_num - context_size - 1)
        end = min(len(lines), line_num + context_size)
        return lines[start:end]

    def _calculate_risk_score(self, findings: List[SecurityFinding], files_analyzed: int, total_lines: int) -> Dict[str, Any]:
        """Calculate overall security risk score."""
        if not findings:
            return {
                'overall_risk': 'low',
                'risk_score': 0.1,
                'description': 'No security vulnerabilities detected'
            }

        # Weight findings by severity
        severity_weights = {
            'critical': 1.0,
            'high': 0.7,
            'medium': 0.4,
            'low': 0.1,
            'info': 0.05
        }

        total_weight = sum(severity_weights.get(f.severity, 0.1) for f in findings)
        avg_weight = total_weight / len(findings)

        # Normalize by code volume
        volume_factor = min(total_lines / 10000, 1.0)  # Cap at 10k lines
        risk_score = avg_weight * volume_factor

        # Determine risk level
        if risk_score >= 0.8:
            risk_level = 'critical'
        elif risk_score >= 0.6:
            risk_level = 'high'
        elif risk_score >= 0.4:
            risk_level = 'medium'
        elif risk_score >= 0.2:
            risk_level = 'low'
        else:
            risk_level = 'minimal'

        return {
            'overall_risk': risk_level,
            'risk_score': round(risk_score, 3),
            'description': f'Security risk assessment: {risk_level} ({risk_score:.1%})',
            'factors': {
                'findings_count': len(findings),
                'avg_severity_weight': round(avg_weight, 3),
                'volume_factor': round(volume_factor, 3)
            }
        }

    def _assess_owasp_coverage(self, findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Assess coverage of OWASP Top 10 categories."""
        owasp_categories = {
            'A01:2021-Broken Access Control': 'Broken Access Control',
            'A02:2021-Cryptographic Failures': 'Cryptographic Failures',
            'A03:2021-Injection': 'Injection',
            'A04:2021-Insecure Design': 'Insecure Design',
            'A05:2021-Security Misconfiguration': 'Security Misconfiguration',
            'A06:2021-Vulnerable Components': 'Vulnerable Components',
            'A07:2021-Identification & Authentication': 'Identification & Authentication',
            'A08:2021-Software Integrity': 'Software Integrity',
            'A09:2021-Security Logging': 'Security Logging',
            'A10:2021-SSRF': 'Server-Side Request Forgery'
        }

        covered_categories = set()
        for finding in findings:
            if finding.owasp_category:
                covered_categories.add(finding.owasp_category)

        return {
            'covered_categories': list(covered_categories),
            'coverage_percentage': round(len(covered_categories) / len(owasp_categories) * 100, 1),
            'total_owasp_categories': len(owasp_categories),
            'covered_count': len(covered_categories)
        }

    def _generate_security_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        if not findings:
            recommendations.append("No critical security issues detected. Continue regular security reviews.")
            return recommendations

        # Group findings by type
        findings_by_type = {}
        for finding in findings:
            vuln_type = finding.vulnerability_type
            if vuln_type not in findings_by_type:
                findings_by_type[vuln_type] = []
            findings_by_type[vuln_type].append(finding)

        # Generate recommendations based on finding types
        if 'sql_injection' in findings_by_type:
            recommendations.append("Implement parameterized queries or prepared statements for all database operations")

        if 'xss_vulnerability' in findings_by_type:
            recommendations.append("Implement proper output encoding and input validation for all user inputs")

        if 'command_injection' in findings_by_type:
            recommendations.append("Avoid shell command execution with user inputs; use safe APIs instead")

        if 'hardcoded_secrets' in findings_by_type:
            recommendations.append("Move all secrets to environment variables or secure credential stores")

        if 'weak_crypto' in findings_by_type:
            recommendations.append("Upgrade to modern cryptographic algorithms (AES-256, SHA-256+)")

        # General recommendations
        critical_count = len([f for f in findings if f.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical security findings immediately")

        recommendations.append("Implement automated security testing in CI/CD pipeline")
        recommendations.append("Conduct regular security code reviews and penetration testing")

        return recommendations

    def _calculate_security_architecture_score(self, findings: List[SecurityFinding], analyzed_files: int, architectural_results: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate security architecture score based on findings."""
        if analyzed_files == 0:
            return {"score": 0.0, "assessment": "No files analyzed"}

        # Base score starts at 50 (neutral)
        score = 50.0

        # Positive indicators (add points)
        positive_patterns = [
            'sandboxing_mechanisms', 'prevention_first_security', 'deterministic_security',
            'offline_security', 'cryptographic_lifecycle', 'multi_layer_validation', 'operational_boundaries'
        ]
        positive_findings = [f for f in findings if f.vulnerability_type in positive_patterns]
        score += len(positive_findings) * 5  # +5 points per positive indicator

        # Use advanced architectural analysis if available
        if architectural_results:
            overall_arch_score = architectural_results.get('overall_architecture_score', 0)
            score = (score + overall_arch_score) / 2  # Average with advanced score

        # Negative indicators (subtract points)
        negative_patterns = [
            'weak_authentication', 'missing_authorization', 'insecure_data_handling', 'trust_boundary_violation'
        ]
        negative_findings = [f for f in findings if f.vulnerability_type in negative_patterns]
        score -= len(negative_findings) * 10  # -10 points per vulnerability

        # Ensure score doesn't go below 0 or above 100
        score = max(0.0, min(100.0, score))

        # Assess architecture quality
        architecture_indicators = negative_patterns
        architecture_vulnerabilities = len(negative_findings)

        assessment = "Excellent" if score >= 90 else "Good" if score >= 70 else "Fair" if score >= 50 else "Poor"

        return {
            "score": score,
            "assessment": assessment,
            "architecture_vulnerabilities": architecture_vulnerabilities,
            "positive_indicators": len(positive_findings),
            "total_vulnerabilities": len(findings)
        }

    def _generate_compliance_matrix(self, findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Generate compliance readiness matrix."""
        compliance_frameworks = {
            'GDPR': ['insecure_data_handling', 'hardcoded_secrets'],
            'SOC2': ['weak_authentication', 'missing_authorization', 'insecure_data_handling'],
            'ISO27001': ['weak_authentication', 'missing_authorization', 'insecure_data_handling', 'trust_boundary_violation'],
            'PCI-DSS': ['hardcoded_secrets', 'weak_crypto', 'insecure_data_handling']
        }

        matrix = {}
        for framework, relevant_patterns in compliance_frameworks.items():
            relevant_findings = [f for f in findings if f.vulnerability_type in relevant_patterns]
            compliance_score = max(0, 100 - len(relevant_findings) * 10)
            readiness = "Compliant" if compliance_score >= 90 else "Mostly Compliant" if compliance_score >= 70 else "Needs Improvement"

            matrix[framework] = {
                "score": compliance_score,
                "readiness": readiness,
                "violations": len(relevant_findings),
                "critical_gaps": [f.description for f in relevant_findings if f.severity in ['critical', 'high']][:3]
            }

        return matrix

    def _assess_threat_model_coverage(self, findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Assess threat model coverage based on findings."""
        threat_categories = {
            'injection': ['sql_injection', 'xss_vulnerability', 'command_injection'],
            'authentication': ['weak_authentication', 'hardcoded_secrets'],
            'authorization': ['missing_authorization', 'path_traversal'],
            'data_protection': ['insecure_data_handling', 'weak_crypto', 'insecure_deserialization'],
            'trust_boundaries': ['trust_boundary_violation']
        }

        coverage = {}
        total_findings = len(findings)

        for category, patterns in threat_categories.items():
            category_findings = [f for f in findings if f.vulnerability_type in patterns]
            coverage_score = max(0, 100 - len(category_findings) * 15)
            coverage[category] = {
                "coverage_score": coverage_score,
                "findings_count": len(category_findings),
                "status": "Well Covered" if coverage_score >= 80 else "Partially Covered" if coverage_score >= 60 else "Needs Attention"
            }

        overall_coverage = sum(c['coverage_score'] for c in coverage.values()) / len(coverage) if coverage else 0

        return {
            "overall_coverage": overall_coverage,
            "categories": coverage,
            "assessment": "Comprehensive" if overall_coverage >= 80 else "Adequate" if overall_coverage >= 60 else "Limited"
        }

    def _finding_to_dict(self, finding: SecurityFinding) -> Dict[str, Any]:
        """Convert SecurityFinding to dictionary."""
        return {
            'vulnerability_type': finding.vulnerability_type,
            'severity': finding.severity,
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'description': finding.description,
            'code_snippet': finding.code_snippet,
            'cwe_id': finding.cwe_id,
            'owasp_category': finding.owasp_category
        }

    def _validated_finding_to_dict(self, finding) -> Dict[str, Any]:
        """Convert ValidatedFinding to dictionary."""
        return {
            'vulnerability_type': finding.vulnerability_type,
            'confidence_level': finding.confidence_level.value,
            'confidence_score': round(finding.confidence_score, 3),
            'validation_factors': {k: round(v, 3) for k, v in finding.validation_factors.items()},
            'evidence_strength': finding.evidence_strength,
            'false_positive_probability': round(finding.false_positive_probability, 3),
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'description': finding.description,
            'code_snippet': finding.code_snippet
        }

def analyze_security_vulnerabilities(file_list: List[str], semantic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for security vulnerability analysis.

    Args:
        file_list: List of file paths to analyze
        semantic: Semantic analysis results from previous stages

    Returns:
        Dict containing security analysis results
    """
    analyzer = SecurityAnalyzer()
    return analyzer.analyze_security_vulnerabilities(file_list, semantic)