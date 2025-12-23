#!/usr/bin/env python3
"""
API Analysis Stage

Analyzes API definitions, REST endpoints, and API design patterns for security,
design quality, and compliance issues. Supports OpenAPI/Swagger, GraphQL,
and common API frameworks.
"""

import json
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse

import logging

logger = logging.getLogger(__name__)

class APIAnalyzer:
    """Analyzes API definitions and patterns for security and quality issues."""

    def __init__(self):
        self.api_files = {
            'openapi': ['openapi.yaml', 'openapi.yml', 'swagger.yaml', 'swagger.yml'],
            'postman': ['*.postman_collection.json'],
            'insomnia': ['*.insomnia.json'],
            'graphql': ['schema.graphql', '*.graphql'],
            'raml': ['*.raml'],
            'api_blueprint': ['*.apib']
        }

        # Common API security issues
        self.security_patterns = {
            'insecure_methods': ['PUT', 'PATCH', 'DELETE'],
            'sensitive_paths': ['/admin', '/internal', '/debug', '/config'],
            'weak_auth': ['Basic', 'API-Key'],
            'missing_validation': ['no_validation', 'no_sanitization']
        }

        # REST API design best practices
        self.design_patterns = {
            'resource_naming': r'^/[a-z][a-z0-9_-]*/?$',
            'http_methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'],
            'status_codes': [200, 201, 204, 400, 401, 403, 404, 409, 422, 500]
        }

    def analyze_api_definitions(self, file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive API analysis.

        Args:
            file_list: List of files to analyze
            semantic_data: Semantic analysis results

        Returns:
            Dict containing API analysis results
        """
        logger.info("Starting API analysis")

        api_results = {
            "api_files_detected": [],
            "api_endpoints": [],
            "security_issues": [],
            "design_issues": [],
            "documentation_issues": [],
            "api_health_score": 100,
            "api_metrics": {
                "total_endpoints": 0,
                "secure_endpoints": 0,
                "documented_endpoints": 0,
                "average_complexity": 0
            },
            "recommendations": [],
            "api_frameworks": []
        }

        # Detect API definition files
        api_files = self._detect_api_files(file_list)

        if not api_files:
            # Look for API patterns in code files
            api_patterns = self._analyze_code_for_api_patterns(file_list)
            if api_patterns:
                api_results["api_endpoints"] = api_patterns
                api_results["api_frameworks"] = ["code_detected"]
        else:
            # Analyze detected API files
            for file_path, api_type in api_files.items():
                try:
                    endpoints = self._parse_api_file(file_path, api_type)
                    if endpoints:
                        api_results["api_files_detected"].append({
                            "file": file_path,
                            "type": api_type,
                            "endpoints": len(endpoints)
                        })
                        api_results["api_endpoints"].extend(endpoints)

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

        # Analyze security issues
        api_results["security_issues"] = self._analyze_security_issues(api_results["api_endpoints"])

        # Analyze design issues
        api_results["design_issues"] = self._analyze_design_issues(api_results["api_endpoints"])

        # Analyze documentation
        api_results["documentation_issues"] = self._analyze_documentation(api_results["api_endpoints"])

        # Calculate metrics
        api_results["api_metrics"] = self._calculate_api_metrics(api_results["api_endpoints"])

        # Calculate API health score
        api_results["api_health_score"] = self._calculate_api_health_score(api_results)

        # Generate recommendations
        api_results["recommendations"] = self._generate_api_recommendations(api_results)

        return api_results

    def _detect_api_files(self, file_list: List[str]) -> Dict[str, str]:
        """Detect API definition files in the repository."""
        api_files = {}

        for file_path in file_list:
            file_name = file_path.split('/')[-1].lower()

            for api_type, patterns in self.api_files.items():
                for pattern in patterns:
                    if pattern.startswith('*.'):
                        # Wildcard pattern
                        if file_name.endswith(pattern[1:]):
                            api_files[file_path] = api_type
                            break
                    elif file_name == pattern:
                        api_files[file_path] = api_type
                        break

        return api_files

    def _parse_api_file(self, file_path: str, api_type: str) -> List[Dict]:
        """Parse an API definition file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if api_type == 'openapi':
                return self._parse_openapi(content)
            elif api_type == 'postman':
                return self._parse_postman(content)
            elif api_type == 'graphql':
                return self._parse_graphql(content)
            else:
                return []

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return []

    def _parse_openapi(self, content: str) -> List[Dict]:
        """Parse OpenAPI/Swagger specification."""
        endpoints = []

        try:
            # Try YAML first, then JSON
            try:
                spec = yaml.safe_load(content)
            except:
                spec = json.loads(content)

            if 'paths' in spec:
                for path, methods in spec['paths'].items():
                    if isinstance(methods, dict):
                        for method, details in methods.items():
                            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                endpoint = {
                                    'path': path,
                                    'method': method.upper(),
                                    'description': details.get('description', ''),
                                    'parameters': details.get('parameters', []),
                                    'responses': list(details.get('responses', {}).keys()),
                                    'security': details.get('security', []),
                                    'source': 'openapi'
                                }
                                endpoints.append(endpoint)

        except Exception as e:
            logger.warning(f"Failed to parse OpenAPI spec: {e}")

        return endpoints

    def _parse_postman(self, content: str) -> List[Dict]:
        """Parse Postman collection."""
        endpoints = []

        try:
            collection = json.loads(content)

            def extract_requests(items):
                for item in items:
                    if 'request' in item:
                        request = item['request']
                        url = request.get('url', {})
                        if isinstance(url, dict) and 'raw' in url:
                            path = url['raw']
                        elif isinstance(url, str):
                            path = url
                        else:
                            path = str(url)

                        endpoint = {
                            'path': path,
                            'method': request.get('method', 'GET'),
                            'description': item.get('name', ''),
                            'parameters': [],
                            'responses': [],
                            'security': [],
                            'source': 'postman'
                        }
                        endpoints.append(endpoint)

                    if 'item' in item:
                        extract_requests(item['item'])

            if 'item' in collection:
                extract_requests(collection['item'])

        except Exception as e:
            logger.warning(f"Failed to parse Postman collection: {e}")

        return endpoints

    def _parse_graphql(self, content: str) -> List[Dict]:
        """Parse GraphQL schema."""
        endpoints = []

        # Basic GraphQL parsing - look for type definitions
        type_pattern = r'type\s+(\w+)\s*{([^}]*)}'
        matches = re.findall(type_pattern, content, re.MULTILINE | re.DOTALL)

        for type_name, fields in matches:
            if type_name not in ['Query', 'Mutation', 'Subscription']:
                continue

            field_lines = [line.strip() for line in fields.split('\n') if line.strip()]
            for field_line in field_lines:
                # Extract field name and return type
                field_match = re.match(r'(\w+)\s*\([^)]*\)\s*:\s*(\w+)', field_line)
                if field_match:
                    field_name, return_type = field_match.groups()
                    endpoint = {
                        'path': f'/{type_name.lower()}/{field_name}',
                        'method': 'GRAPHQL',
                        'description': f'{type_name} {field_name}',
                        'parameters': [],
                        'responses': [return_type],
                        'security': [],
                        'source': 'graphql'
                    }
                    endpoints.append(endpoint)

        return endpoints

    def _analyze_code_for_api_patterns(self, file_list: List[str]) -> List[Dict]:
        """Analyze code files for API patterns."""
        endpoints = []

        # Common API framework patterns
        framework_patterns = {
            'flask': [
                (r'@app\.route\(["\']([^"\']+)["\']', 'GET'),
                (r'@app\.route\(["\']([^"\']+)["\'], methods=\[([^\]]+)\]', None)
            ],
            'django': [
                (r'path\(["\']([^"\']+)["\']', 'GET'),
                (r'url\(["\']([^"\']+)["\']', 'GET')
            ],
            'express': [
                (r'app\.(get|post|put|delete)\(["\']([^"\']+)["\']', None)
            ],
            'spring': [
                (r'@RequestMapping\(["\']([^"\']+)["\']', 'GET'),
                (r'@GetMapping\(["\']([^"\']+)["\']', 'GET'),
                (r'@PostMapping\(["\']([^"\']+)["\']', 'POST')
            ]
        }

        for file_path in file_list:
            if not file_path.endswith(('.py', '.js', '.java')):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for framework, patterns in framework_patterns.items():
                    for pattern, default_method in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            if isinstance(match, tuple):
                                method = match[0].upper()
                                path = match[1]
                            else:
                                method = default_method or 'GET'
                                path = match

                            endpoint = {
                                'path': path,
                                'method': method,
                                'description': f'Detected in {file_path}',
                                'parameters': [],
                                'responses': [],
                                'security': [],
                                'source': f'code_{framework}'
                            }
                            endpoints.append(endpoint)

            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        return endpoints

    def _analyze_security_issues(self, endpoints: List[Dict]) -> List[Dict]:
        """Analyze endpoints for security issues."""
        security_issues = []

        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', '')

            # Check for insecure HTTP methods on sensitive paths
            if method in self.security_patterns['insecure_methods']:
                for sensitive_path in self.security_patterns['sensitive_paths']:
                    if sensitive_path in path.lower():
                        security_issues.append({
                            'endpoint': f"{method} {path}",
                            'issue': f'Insecure {method} method on sensitive path',
                            'severity': 'high',
                            'type': 'insecure_method'
                        })

            # Check for missing authentication
            security = endpoint.get('security', [])
            if not security and any(word in path.lower() for word in ['admin', 'user', 'private']):
                security_issues.append({
                    'endpoint': f"{method} {path}",
                    'issue': 'Missing authentication on protected endpoint',
                    'severity': 'medium',
                    'type': 'missing_auth'
                })

            # Check for weak authentication methods
            for sec in security:
                if isinstance(sec, dict):
                    for auth_type in sec.keys():
                        if auth_type in self.security_patterns['weak_auth']:
                            security_issues.append({
                                'endpoint': f"{method} {path}",
                                'issue': f'Weak authentication method: {auth_type}',
                                'severity': 'medium',
                                'type': 'weak_auth'
                            })

        return security_issues

    def _analyze_design_issues(self, endpoints: List[Dict]) -> List[Dict]:
        """Analyze endpoints for design issues."""
        design_issues = []

        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', '')

            # Check resource naming conventions
            if not re.match(self.design_patterns['resource_naming'], path):
                design_issues.append({
                    'endpoint': f"{method} {path}",
                    'issue': 'Non-standard resource naming',
                    'severity': 'low',
                    'type': 'naming_convention'
                })

            # Check HTTP method usage
            if method not in self.design_patterns['http_methods']:
                design_issues.append({
                    'endpoint': f"{method} {path}",
                    'issue': f'Non-standard HTTP method: {method}',
                    'severity': 'medium',
                    'type': 'http_method'
                })

            # Check for proper response codes
            responses = endpoint.get('responses', [])
            if responses and not any(int(code) in self.design_patterns['status_codes'] for code in responses if code.isdigit()):
                design_issues.append({
                    'endpoint': f"{method} {path}",
                    'issue': 'Non-standard HTTP status codes',
                    'severity': 'low',
                    'type': 'status_codes'
                })

        return design_issues

    def _analyze_documentation(self, endpoints: List[Dict]) -> List[Dict]:
        """Analyze endpoints for documentation issues."""
        documentation_issues = []

        for endpoint in endpoints:
            description = endpoint.get('description', '').strip()

            if not description:
                documentation_issues.append({
                    'endpoint': f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
                    'issue': 'Missing endpoint description',
                    'severity': 'low',
                    'type': 'missing_description'
                })

            # Check for parameter documentation
            parameters = endpoint.get('parameters', [])
            if parameters and not description:
                documentation_issues.append({
                    'endpoint': f"{endpoint.get('method', '')} {endpoint.get('path', '')}",
                    'issue': 'Parameters defined but not documented',
                    'severity': 'medium',
                    'type': 'undocumented_parameters'
                })

        return documentation_issues

    def _calculate_api_metrics(self, endpoints: List[Dict]) -> Dict[str, Any]:
        """Calculate API metrics."""
        total_endpoints = len(endpoints)
        secure_endpoints = 0
        documented_endpoints = 0

        for endpoint in endpoints:
            # Count secure endpoints
            if endpoint.get('security'):
                secure_endpoints += 1

            # Count documented endpoints
            if endpoint.get('description', '').strip():
                documented_endpoints += 1

        return {
            "total_endpoints": total_endpoints,
            "secure_endpoints": secure_endpoints,
            "documented_endpoints": documented_endpoints,
            "average_complexity": 0  # Placeholder for future complexity analysis
        }

    def _calculate_api_health_score(self, results: Dict) -> float:
        """Calculate overall API health score."""
        base_score = 100

        # Deduct points for security issues
        security_count = len(results["security_issues"])
        base_score -= min(security_count * 5, 30)

        # Deduct points for design issues
        design_count = len(results["design_issues"])
        base_score -= min(design_count * 2, 20)

        # Deduct points for documentation issues
        doc_count = len(results["documentation_issues"])
        base_score -= min(doc_count * 1, 15)

        # Bonus for having API definitions
        if results["api_files_detected"]:
            base_score += 10

        # Bonus for security coverage
        metrics = results["api_metrics"]
        if metrics["total_endpoints"] > 0:
            security_ratio = metrics["secure_endpoints"] / metrics["total_endpoints"]
            base_score += min(security_ratio * 10, 10)

        return max(0, base_score)

    def _generate_api_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on API analysis."""
        recommendations = []

        if results["security_issues"]:
            recommendations.append(f"Address {len(results['security_issues'])} API security vulnerabilities")

        if results["design_issues"]:
            recommendations.append(f"Fix {len(results['design_issues'])} API design issues")

        if results["documentation_issues"]:
            recommendations.append(f"Improve documentation for {len(results['documentation_issues'])} endpoints")

        if not results["api_files_detected"] and not results["api_endpoints"]:
            recommendations.append("Consider creating API documentation (OpenAPI/Swagger)")

        if results["api_health_score"] < 70:
            recommendations.append("Overall API health needs improvement - conduct API audit")

        if not recommendations:
            recommendations.append("API design and security appear adequate")

        return recommendations


def analyze_api_definitions(file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze API definitions for security, design, and documentation issues.

    Args:
        file_list: List of files to analyze
        semantic_data: Semantic analysis results

    Returns:
        Dict containing API analysis results
    """
    analyzer = APIAnalyzer()
    return analyzer.analyze_api_definitions(file_list, semantic_data)
