"""Documentation Accuracy Analysis for Repository Intelligence Scanner.

This module analyzes documentation (primarily README.md files) to extract claims
and assess their accuracy against the actual codebase implementation.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import logging

logger = logging.getLogger(__name__)


class DocumentationAnalyzer:
    """Analyzes documentation for claims and accuracy assessment."""

    def __init__(self):
        self.readme_patterns = [
            'README.md', 'README.rst', 'README.txt', 'README',
            'readme.md', 'readme.rst', 'readme.txt', 'readme'
        ]

        self.claims_patterns = {
            'features': [
                r'(?:^|\n)##?\s*(?:Features?|Capabilities?|What\s+(?:it|this)\s+(?:does?|can|provides?))\s*$',
                r'(?:^|\n)#+\s*(?:Features?|Capabilities?|Functionality)\s*$',
                r'(?:^|\n)\*\s*(?:Supports?|Provides?|Includes?|Offers?)\s+(.+)',
                r'(?:^|\n)-\s*(?:Supports?|Provides?|Includes?|Offers?)\s+(.+)'
            ],
            'requirements': [
                r'(?:^|\n)##?\s*(?:Requirements?|Prerequisites?|Dependencies?)\s*$',
                r'(?:^|\n)#+\s*(?:Requirements?|Prerequisites?|Dependencies?)\s*$',
                r'Requires?\s+(?:Python|Node|Java|etc\.?)\s+[\d\.]+',
                r'Depends?\s+on\s+(.+)'
            ],
            'installation': [
                r'(?:^|\n)##?\s*(?:Installation|Install|Setup)\s*$',
                r'(?:^|\n)#+\s*(?:Installation|Install|Setup)\s*$',
                r'(?:^|\n)```\s*(?:bash|sh|shell)\s*$',
                r'pip\s+install',
                r'npm\s+install',
                r'mvn\s+install'
            ],
            'usage': [
                r'(?:^|\n)##?\s*(?:Usage|Examples?|Quick\s+Start)\s*$',
                r'(?:^|\n)#+\s*(?:Usage|Examples?|Quick\s+Start)\s*$',
                r'(?:^|\n)```\s*(?:python|bash|javascript|java)\s*$'
            ],
            'api': [
                r'(?:^|\n)##?\s*(?:API|Interface|Endpoints?)\s*$',
                r'(?:^|\n)#+\s*(?:API|Interface|Endpoints?)\s*$',
                r'GET\s+/.+',
                r'POST\s+/.+',
                r'PUT\s+/.+',
                r'DELETE\s+/.+'
            ]
        }

    def analyze_documentation_accuracy(self, repository_path: str, file_list: List[str]) -> Dict[str, Any]:
        """Analyze documentation accuracy by extracting claims and comparing with implementation."""
        # Find README files
        readme_files = self._find_readme_files(repository_path, file_list)

        # Parse README files for claims
        documentation_claims = {}
        for readme_file in readme_files:
            claims = self._parse_readme_claims(readme_file)
            documentation_claims[readme_file] = claims

        # Analyze claims vs implementation
        claims_analysis = self._analyze_claims_vs_implementation(documentation_claims, file_list)

        return {
            "readme_files": readme_files,
            "documentation_claims": documentation_claims,
            "claims_analysis": claims_analysis,
            "accuracy_score": self._calculate_accuracy_score(claims_analysis),
            "evidence_based_findings": self._generate_evidence_based_findings(claims_analysis)
        }

    def _find_readme_files(self, repository_path: str, file_list: List[str]) -> List[str]:
        """Find README files in the repository."""
        readme_files = []

        for file_path in file_list:
            filename = os.path.basename(file_path).lower()
            if filename in [pattern.lower() for pattern in self.readme_patterns]:
                readme_files.append(file_path)

        # Also check common locations
        common_locations = [
            'README.md', 'README.rst', 'README.txt',
            'docs/README.md', 'docs/README.rst', 'docs/README.txt'
        ]

        for location in common_locations:
            full_path = os.path.join(repository_path, location)
            if os.path.exists(full_path) and full_path not in readme_files:
                readme_files.append(full_path)

        return readme_files

    def _parse_readme_claims(self, readme_file: str) -> Dict[str, Any]:
        """Parse a README file to extract claims and features."""
        try:
            with open(readme_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, OSError):
            logger.warning(f"Could not read README file: {readme_file}")
            return {}

        claims = {
            'features': self._extract_features(content),
            'requirements': self._extract_requirements(content),
            'installation': self._extract_installation(content),
            'usage': self._extract_usage(content),
            'api': self._extract_api(content),
            'metadata': self._extract_metadata(content)
        }

        return claims

    def _extract_features(self, content: str) -> List[Dict[str, Any]]:
        """Extract feature claims from documentation."""
        features = []

        for pattern in self.claims_patterns['features']:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1] if len(match) > 1 else str(match)

                feature_text = match.strip()
                if feature_text and len(feature_text) > 10:  # Filter out very short matches
                    features.append({
                        'text': feature_text,
                        'type': 'feature_claim',
                        'confidence': self._calculate_claim_confidence(feature_text)
                    })

        return features

    def _extract_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract requirement claims from documentation."""
        requirements = []

        for pattern in self.claims_patterns['requirements']:
            matches = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else str(match)

                req_text = match.strip()
                if req_text and len(req_text) > 5:
                    requirements.append({
                        'text': req_text,
                        'type': 'requirement_claim',
                        'confidence': self._calculate_claim_confidence(req_text)
                    })

        return requirements

    def _extract_installation(self, content: str) -> List[Dict[str, Any]]:
        """Extract installation claims from documentation."""
        installation = []

        # Look for installation sections
        install_section_pattern = r'(?:^|\n)#{1,3}\s*(?:Installation|Install|Setup|Getting\s+Started)\s*\n(.*?)(?:\n#{1,3}|\n##|\Z)'
        install_match = re.search(install_section_pattern, content, re.DOTALL | re.IGNORECASE)

        if install_match:
            install_content = install_match.group(1)
            # Extract commands
            commands = re.findall(r'`([^`]+)`', install_content)
            for cmd in commands:
                if any(keyword in cmd.lower() for keyword in ['pip', 'npm', 'mvn', 'gradle', 'install', 'setup']):
                    installation.append({
                        'text': cmd,
                        'type': 'installation_command',
                        'confidence': 0.9
                    })

        return installation

    def _extract_usage(self, content: str) -> List[Dict[str, Any]]:
        """Extract usage examples from documentation."""
        usage = []

        # Look for usage sections
        usage_section_pattern = r'(?:^|\n)#{1,3}\s*(?:Usage|Examples?|Quick\s+Start|Getting\s+Started)\s*\n(.*?)(?:\n#{1,3}|\n##|\Z)'
        usage_match = re.search(usage_section_pattern, content, re.DOTALL | re.IGNORECASE)

        if usage_match:
            usage_content = usage_match.group(1)
            # Extract code blocks
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', usage_content, re.DOTALL)
            for block in code_blocks:
                usage.append({
                    'text': block.strip(),
                    'type': 'usage_example',
                    'confidence': 0.8
                })

        return usage

    def _extract_api(self, content: str) -> List[Dict[str, Any]]:
        """Extract API claims from documentation."""
        api = []

        # Look for API sections
        api_section_pattern = r'(?:^|\n)#{1,3}\s*(?:API|Interface|Endpoints?)\s*\n(.*?)(?:\n#{1,3}|\n##|\Z)'
        api_match = re.search(api_section_pattern, content, re.DOTALL | re.IGNORECASE)

        if api_match:
            api_content = api_match.group(1)
            # Extract HTTP methods and endpoints
            http_patterns = [
                r'(GET|POST|PUT|DELETE|PATCH)\s+([^\s\n]+)',
                r'`(GET|POST|PUT|DELETE|PATCH)\s+([^`]+)`'
            ]

            for pattern in http_patterns:
                matches = re.findall(pattern, api_content, re.IGNORECASE)
                for match in matches:
                    method, endpoint = match
                    api.append({
                        'text': f'{method.upper()} {endpoint}',
                        'type': 'api_endpoint',
                        'method': method.upper(),
                        'endpoint': endpoint,
                        'confidence': 0.9
                    })

        return api

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from README."""
        metadata = {}

        # Extract title
        title_match = re.search(r'^#\s*(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()

        # Extract description
        desc_match = re.search(r'^#\s*.+\n\n(.+?)(?:\n\n|\n#|\Z)', content, re.DOTALL)
        if desc_match:
            metadata['description'] = desc_match.group(1).strip()

        # Extract badges
        badges = re.findall(r'!\[([^\]]+)\]\([^\)]+\)', content)
        if badges:
            metadata['badges'] = badges

        return metadata

    def _calculate_claim_confidence(self, claim_text: str) -> float:
        """Calculate confidence score for a claim based on its specificity."""
        confidence = 0.5  # Base confidence

        # Increase confidence for specific technical terms
        technical_indicators = [
            'algorithm', 'implementation', 'library', 'framework', 'api',
            'database', 'security', 'authentication', 'encryption',
            'performance', 'optimization', 'compatibility'
        ]

        if any(indicator in claim_text.lower() for indicator in technical_indicators):
            confidence += 0.2

        # Increase confidence for version numbers
        if re.search(r'\d+\.\d+', claim_text):
            confidence += 0.1

        # Increase confidence for code-like elements
        if re.search(r'`[^`]+`', claim_text):
            confidence += 0.1

        # Decrease confidence for vague terms
        vague_terms = ['easy', 'simple', 'fast', 'powerful', 'amazing', 'best']
        if any(term in claim_text.lower() for term in vague_terms):
            confidence -= 0.1

        return max(0.1, min(1.0, confidence))

    def _analyze_claims_vs_implementation(self, documentation_claims: Dict, file_list: List[str]) -> Dict[str, Any]:
        """Analyze documentation claims against actual implementation."""
        analysis = {
            'feature_claims': [],
            'requirement_claims': [],
            'installation_claims': [],
            'usage_claims': [],
            'api_claims': [],
            'verification_status': {}
        }

        # Analyze each README file
        for readme_file, claims in documentation_claims.items():
            for claim_type, claim_list in claims.items():
                if claim_type == 'metadata':
                    continue

                for claim in claim_list:
                    verification = self._verify_claim(claim, file_list)
                    analysis[f'{claim_type}_claims'].append({
                        'claim': claim,
                        'verification': verification,
                        'readme_file': readme_file
                    })

        # Calculate verification status
        analysis['verification_status'] = self._calculate_verification_status(analysis)

        return analysis

    def _verify_claim(self, claim: Dict[str, Any], file_list: List[str]) -> Dict[str, Any]:
        """Verify a documentation claim against the codebase."""
        claim_text = claim['text'].lower()
        claim_type = claim['type']

        verification = {
            'verified': False,
            'evidence': [],
            'confidence': 0.0,
            'issues': []
        }

        if claim_type == 'feature_claim':
            verification = self._verify_feature_claim(claim_text, file_list)
        elif claim_type == 'requirement_claim':
            verification = self._verify_requirement_claim(claim_text, file_list)
        elif claim_type == 'installation_command':
            verification = self._verify_installation_claim(claim_text, file_list)
        elif claim_type == 'usage_example':
            verification = self._verify_usage_claim(claim_text, file_list)
        elif claim_type == 'api_endpoint':
            verification = self._verify_api_claim(claim, file_list)

        return verification

    def _verify_feature_claim(self, claim_text: str, file_list: List[str]) -> Dict[str, Any]:
        """Verify a feature claim by looking for implementation evidence."""
        verification = {
            'verified': False,
            'evidence': [],
            'confidence': 0.0,
            'issues': []
        }

        # Look for keywords in file names and content
        keywords = self._extract_keywords_from_claim(claim_text)

        evidence_found = 0
        total_checks = 0

        for keyword in keywords:
            total_checks += 1
            if self._keyword_found_in_codebase(keyword, file_list):
                evidence_found += 1
                verification['evidence'].append(f"Found '{keyword}' in codebase")

        if total_checks > 0:
            verification['confidence'] = evidence_found / total_checks
            verification['verified'] = verification['confidence'] > 0.5

        if not verification['verified']:
            verification['issues'].append("Feature claim not supported by implementation")

        return verification

    def _verify_requirement_claim(self, claim_text: str, file_list: List[str]) -> Dict[str, Any]:
        """Verify a requirement claim."""
        verification = {
            'verified': False,
            'evidence': [],
            'confidence': 0.0,
            'issues': []
        }

        # Check for common requirement patterns
        if 'python' in claim_text:
            python_files = [f for f in file_list if f.endswith('.py')]
            if python_files:
                verification['verified'] = True
                verification['evidence'].append(f"Found {len(python_files)} Python files")
                verification['confidence'] = 0.9
        elif 'node' in claim_text or 'npm' in claim_text:
            js_files = [f for f in file_list if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]
            if js_files:
                verification['verified'] = True
                verification['evidence'].append(f"Found {len(js_files)} JavaScript/TypeScript files")
                verification['confidence'] = 0.9

        return verification

    def _verify_installation_claim(self, claim_text: str, file_list: List[str]) -> Dict[str, Any]:
        """Verify an installation claim."""
        verification = {
            'verified': False,
            'evidence': [],
            'confidence': 0.0,
            'issues': []
        }

        # Check if installation files exist
        if 'pip install' in claim_text:
            setup_files = [f for f in file_list if os.path.basename(f) in ['setup.py', 'pyproject.toml', 'requirements.txt']]
            if setup_files:
                verification['verified'] = True
                verification['evidence'].extend([f"Found {f}" for f in setup_files])
                verification['confidence'] = 0.8
        elif 'npm install' in claim_text:
            package_files = [f for f in file_list if os.path.basename(f) == 'package.json']
            if package_files:
                verification['verified'] = True
                verification['evidence'].extend([f"Found {f}" for f in package_files])
                verification['confidence'] = 0.8

        return verification

    def _verify_usage_claim(self, claim_text: str, file_list: List[str]) -> Dict[str, Any]:
        """Verify a usage claim."""
        verification = {
            'verified': True,  # Usage examples are harder to verify automatically
            'evidence': ['Usage example present in documentation'],
            'confidence': 0.6,
            'issues': []
        }
        return verification

    def _verify_api_claim(self, claim: Dict[str, Any], file_list: List[str]) -> Dict[str, Any]:
        """Verify an API claim."""
        verification = {
            'verified': False,
            'evidence': [],
            'confidence': 0.0,
            'issues': []
        }

        endpoint = claim.get('endpoint', '')
        method = claim.get('method', '')

        # Look for API-related files
        api_files = [f for f in file_list if any(keyword in f.lower() for keyword in ['api', 'route', 'endpoint', 'handler'])]

        if api_files:
            verification['verified'] = True
            verification['evidence'].append(f"Found {len(api_files)} API-related files")
            verification['confidence'] = 0.7

        return verification

    def _extract_keywords_from_claim(self, claim_text: str) -> List[str]:
        """Extract keywords from a claim for verification."""
        # Remove common stop words and punctuation
        words = re.findall(r'\b\w+\b', claim_text.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}

        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords

    def _keyword_found_in_codebase(self, keyword: str, file_list: List[str]) -> bool:
        """Check if a keyword is found in the codebase."""
        # This is a simplified check - in practice would search file contents
        for file_path in file_list:
            if keyword in file_path.lower():
                return True
        return False

    def _calculate_verification_status(self, analysis: Dict) -> Dict[str, Any]:
        """Calculate overall verification status."""
        total_claims = 0
        verified_claims = 0

        for claim_type in ['feature_claims', 'requirement_claims', 'installation_claims', 'usage_claims', 'api_claims']:
            claims = analysis.get(claim_type, [])
            total_claims += len(claims)
            verified_claims += len([c for c in claims if c['verification']['verified']])

        return {
            'total_claims': total_claims,
            'verified_claims': verified_claims,
            'verification_rate': verified_claims / max(1, total_claims),
            'unverified_claims': total_claims - verified_claims
        }

    def _calculate_accuracy_score(self, claims_analysis: Dict) -> float:
        """Calculate overall documentation accuracy score."""
        verification_status = claims_analysis.get('verification_status', {})
        verification_rate = verification_status.get('verification_rate', 0.0)

        # Weight different factors
        base_score = verification_rate * 0.8

        # Bonus for having documentation
        if verification_status.get('total_claims', 0) > 0:
            base_score += 0.1

        # Penalty for unverified claims
        unverified_rate = verification_status.get('unverified_claims', 0) / max(1, verification_status.get('total_claims', 1))
        base_score -= unverified_rate * 0.1

        return max(0.0, min(1.0, base_score))

    def _generate_evidence_based_findings(self, claims_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate evidence-based findings about documentation accuracy."""
        findings = []

        verification_status = claims_analysis.get('verification_status', {})

        if verification_status.get('verification_rate', 0) > 0.8:
            findings.append({
                'type': 'positive',
                'category': 'documentation_accuracy',
                'title': 'High documentation accuracy',
                'description': 'Documentation claims are well-supported by implementation',
                'evidence': [f"{verification_status.get('verified_claims', 0)}/{verification_status.get('total_claims', 0)} claims verified"],
                'confidence': 0.9
            })
        elif verification_status.get('verification_rate', 0) < 0.5:
            findings.append({
                'type': 'issue',
                'category': 'documentation_accuracy',
                'title': 'Low documentation accuracy',
                'description': 'Many documentation claims are not supported by implementation',
                'evidence': [f"Only {verification_status.get('verified_claims', 0)}/{verification_status.get('total_claims', 0)} claims verified"],
                'confidence': 0.8
            })

        # Check for specific unverified claims
        for claim_type in ['feature_claims', 'requirement_claims', 'installation_claims']:
            claims = claims_analysis.get(claim_type, [])
            unverified = [c for c in claims if not c['verification']['verified']]

            if len(unverified) > 0:
                findings.append({
                    'type': 'issue',
                    'category': 'documentation_accuracy',
                    'title': f'Unverified {claim_type.replace("_claims", "")} claims',
                    'description': f'{len(unverified)} {claim_type.replace("_claims", "")} claims could not be verified',
                    'evidence': [c['claim']['text'] for c in unverified[:3]],  # Show first 3
                    'confidence': 0.7
                })

        return findings


def analyze_documentation_accuracy(repository_path: str, file_list: List[str]) -> Dict[str, Any]:
    """Main entry point for documentation accuracy analysis."""
    analyzer = DocumentationAnalyzer()
    return analyzer.analyze_documentation_accuracy(repository_path, file_list)