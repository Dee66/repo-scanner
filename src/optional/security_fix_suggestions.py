"""
Security Fix Suggestions Module

Provides automated suggestions for fixing detected security vulnerabilities.
"""

from typing import Dict, Any, List
import re


class SecurityFixSuggester:
    """
    Generates automated fix suggestions for security vulnerabilities.
    """

    def __init__(self):
        self.fix_templates = {
            "hardcoded_secret": {
                "description": "Replace hardcoded secret with environment variable or secure key management",
                "patterns": [
                    r"password\s*=\s*['\"]([^'\"]*)['\"]",
                    r"secret\s*=\s*['\"]([^'\"]*)['\"]",
                    r"key\s*=\s*['\"]([^'\"]*)['\"]",
                    r"token\s*=\s*['\"]([^'\"]*)['\"]"
                ],
                "suggestion": "Use environment variables: os.getenv('SECRET_KEY') or secure key management service"
            },
            "sql_injection": {
                "description": "Use parameterized queries to prevent SQL injection",
                "patterns": [
                    r"execute\s*\(\s*['\"](SELECT|INSERT|UPDATE|DELETE).*?\+.*?\)",
                    r"cursor\.execute\s*\(\s*f['\"](SELECT|INSERT|UPDATE|DELETE).*?\{.*?\}.*?['\"]\s*\)"
                ],
                "suggestion": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
            },
            "xss_vulnerability": {
                "description": "Sanitize user input to prevent XSS attacks",
                "patterns": [
                    r"innerHTML\s*=\s*.*?(input|param|getParameter)",
                    r"document\.write\s*\(\s*.*?(input|param|getParameter)"
                ],
                "suggestion": "Use textContent instead of innerHTML, or sanitize input with DOMPurify"
            },
            "insecure_random": {
                "description": "Use cryptographically secure random number generation",
                "patterns": [
                    r"import random",
                    r"random\.(randint|choice|shuffle)"
                ],
                "suggestion": "Use secrets module: import secrets; secrets.token_hex(16)"
            },
            "weak_crypto": {
                "description": "Use strong cryptographic algorithms",
                "patterns": [
                    r"md5\(",
                    r"sha1\(",
                    r"DES\(",
                    r"RC4\("
                ],
                "suggestion": "Use SHA-256 or higher: hashlib.sha256(data.encode()).hexdigest()"
            },
            "path_traversal": {
                "description": "Validate and sanitize file paths",
                "patterns": [
                    r"open\s*\(\s*.*?(input|param|getParameter)",
                    r"os\.path\.join\s*\(\s*.*?(input|param|getParameter)"
                ],
                "suggestion": "Validate paths: os.path.abspath(path).startswith(allowed_dir)"
            },
            "command_injection": {
                "description": "Avoid shell command injection",
                "patterns": [
                    r"subprocess\.call\s*\(\s*.*?(input|param|getParameter)",
                    r"os\.system\s*\(\s*.*?(input|param|getParameter)"
                ],
                "suggestion": "Use subprocess with list arguments: subprocess.run(['ls', safe_arg])"
            }
        }

    def generate_fix_suggestions(self, security_analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fix suggestions based on security analysis results.

        Args:
            security_analysis_results: Results from security vulnerability analysis

        Returns:
            Dict containing fix suggestions
        """
        suggestions = {
            "total_suggestions": 0,
            "high_priority_fixes": [],
            "medium_priority_fixes": [],
            "low_priority_fixes": [],
            "fix_details": {}
        }

        # Process patterns by language
        patterns_by_language = security_analysis_results.get("patterns_by_language", {})

        for language, files in patterns_by_language.items():
            for file_entry in files:
                for pattern in file_entry.get("patterns", []):
                    fix_suggestion = self._generate_fix_for_pattern(pattern, language)
                    if fix_suggestion:
                        suggestions["total_suggestions"] += 1
                        key = pattern.get("id", f"{language}_{len(suggestions['fix_details'])}")
                        suggestions["fix_details"][key] = fix_suggestion

                        severity = pattern.get("severity", "medium")
                        if severity in ("high", "critical"):
                            suggestions["high_priority_fixes"].append(fix_suggestion)
                        elif severity == "medium":
                            suggestions["medium_priority_fixes"].append(fix_suggestion)
                        else:
                            suggestions["low_priority_fixes"].append(fix_suggestion)

        return suggestions

    def _generate_fix_for_pattern(self, pattern: Dict[str, Any], language: str) -> Dict[str, Any]:
        """
        Generate a fix suggestion for a specific security pattern.

        Args:
            pattern: Security pattern details
            language: Programming language

        Returns:
            Dict containing fix suggestion details
        """
        pattern_type = pattern.get("pattern") or pattern.get("type", "")
        description = pattern.get("description", "")
        file_path = pattern.get("file", "")
        line_number = pattern.get("line", 0)

        # Find matching fix template
        fix_template = None
        for template_key, template in self.fix_templates.items():
            if template_key.lower() in pattern_type.lower() or template_key.lower() in description.lower():
                fix_template = template
                break

        if not fix_template:
            # Generic fix suggestion
            fix_template = {
                "description": f"Review and fix {pattern_type} vulnerability",
                "suggestion": "Consult security best practices and implement appropriate safeguards"
            }

        return {
            "vulnerability_type": pattern_type,
            "description": description,
            "file": file_path,
            "line": line_number,
            "language": language,
            "severity": pattern.get("severity", "medium"),
            "fix_description": fix_template["description"],
            "suggested_fix": fix_template["suggestion"],
            "code_example": self._generate_code_example(pattern_type, language),
            "references": self._get_security_references(pattern_type)
        }

    def _generate_code_example(self, vulnerability_type: str, language: str) -> str:
        """
        Generate a code example for fixing the vulnerability.

        Args:
            vulnerability_type: Type of vulnerability
            language: Programming language

        Returns:
            Code example string
        """
        examples = {
            "hardcoded_secret": {
                "python": "import os\nsecret_key = os.getenv('SECRET_KEY')\nif not secret_key:\n    raise ValueError('SECRET_KEY environment variable not set')",
                "javascript": "const secretKey = process.env.SECRET_KEY;\nif (!secretKey) {\n    throw new Error('SECRET_KEY environment variable not set');\n}",
                "java": "String secretKey = System.getenv(\"SECRET_KEY\");\nif (secretKey == null) {\n    throw new RuntimeException(\"SECRET_KEY environment variable not set\");\n}"
            },
            "sql_injection": {
                "python": "import sqlite3\ncursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
                "javascript": "const query = 'SELECT * FROM users WHERE id = ?';\nconnection.query(query, [userId]);",
                "java": "String query = \"SELECT * FROM users WHERE id = ?\";\nPreparedStatement stmt = conn.prepareStatement(query);\nstmt.setInt(1, userId);"
            },
            "xss_vulnerability": {
                "javascript": "element.textContent = userInput; // Safe\n// Instead of: element.innerHTML = userInput; // Unsafe"
            }
        }

        vuln_examples = examples.get(vulnerability_type, {})
        return vuln_examples.get(language, "// Consult security documentation for proper implementation")

    def _get_security_references(self, vulnerability_type: str) -> List[str]:
        """
        Get security references for the vulnerability type.

        Args:
            vulnerability_type: Type of vulnerability

        Returns:
            List of reference URLs or resources
        """
        references = {
            "hardcoded_secret": [
                "OWASP: https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password",
                "NIST: SP 800-63B - Authentication and Lifecycle Management"
            ],
            "sql_injection": [
                "OWASP: https://owasp.org/www-community/attacks/SQL_Injection",
                "NIST: SP 800-95 - Guide to Secure Web Services"
            ],
            "xss_vulnerability": [
                "OWASP: https://owasp.org/www-community/attacks/xss/",
                "NIST: SP 800-53 - Security and Privacy Controls"
            ],
            "command_injection": [
                "OWASP: https://owasp.org/www-community/attacks/Command_Injection",
                "NIST: SP 800-53 - System and Information Integrity"
            ]
        }

        return references.get(vulnerability_type, ["OWASP Top 10: https://owasp.org/www-project-top-ten/"])