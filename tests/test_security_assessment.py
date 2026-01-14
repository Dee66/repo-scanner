"""Security testing and vulnerability assessment infrastructure."""

import pytest
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import subprocess
import tempfile
import os

# Use absolute path based on conftest.py location
_conf_dir = Path(__file__).parent

# Security testing configuration
_security_config_file = _conf_dir / ".pytest_cache" / "security_config.json"
_vulnerability_report_file = _conf_dir / ".pytest_cache" / "vulnerability_report.json"
_security_scan_results = []

# Common vulnerability patterns
VULNERABILITY_PATTERNS = {
    "sql_injection": [
        r"SELECT.*\+.*",
        r"INSERT.*\+.*",
        r"UPDATE.*\+.*",
        r"DELETE.*\+.*",
        r"execute.*\+.*",
        r"raw.*\+.*"
    ],
    "xss": [
        r"innerHTML.*\+.*",
        r"outerHTML.*\+.*",
        r"document\.write.*\+.*",
        r"eval\(.*\+.*",
        r"setTimeout\(.*\+.*",
        r"setInterval\(.*\+.*"
    ],
    "command_injection": [
        r"os\.system\(.*\+.*",
        r"subprocess\.call\(.*\+.*",
        r"subprocess\.run\(.*\+.*",
        r"exec\(.*\+.*",
        r"eval\(.*\+.*",
        r"shell=True.*\+.*"
    ],
    "path_traversal": [
        r"\.\./.*",
        r"\.\.\\.*",
        r"\\.\\.*",
        r"/\.\./.*"
    ],
    "hardcoded_secrets": [
        r"password.*=.*['\"][^'\"]*['\"]",
        r"secret.*=.*['\"][^'\"]*['\"]",
        r"key.*=.*['\"][^'\"]*['\"]",
        r"token.*=.*['\"][^'\"]*['\"]",
        r"api_key.*=.*['\"][^'\"]*['\"]"
    ],
    "insecure_random": [
        r"random\.random\(\)",
        r"random\.randint\(",
        r"random\.choice\("
    ]
}

# Security severity levels
SEVERITY_LEVELS = {
    "critical": 9,
    "high": 7,
    "medium": 5,
    "low": 3,
    "info": 1
}


def load_security_config():
    """Load security testing configuration."""
    if _security_config_file.exists():
        try:
            with open(_security_config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "enabled_scanners": ["static_analysis", "input_validation", "dependency_check"],
        "severity_threshold": "medium",
        "fail_on_vulnerabilities": False,
        "scan_directories": ["src", "tests"],
        "exclude_patterns": ["*.pyc", "__pycache__", ".git"],
        "max_scan_depth": 10,
        "timeout": 300
    }


def save_security_config(config):
    """Save security testing configuration."""
    _security_config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_security_config_file, 'w') as f:
        json.dump(config, f, indent=2)


def load_vulnerability_report():
    """Load vulnerability assessment report."""
    if _vulnerability_report_file.exists():
        try:
            with open(_vulnerability_report_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_vulnerability_report(report):
    """Save vulnerability assessment report."""
    _vulnerability_report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_vulnerability_report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)


def scan_for_vulnerabilities(file_path: Path, content: str) -> List[Dict[str, Any]]:
    """Scan a file for common vulnerabilities."""
    vulnerabilities = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        for vuln_type, patterns in VULNERABILITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Calculate severity based on vulnerability type
                    severity = "medium"
                    if vuln_type in ["sql_injection", "command_injection"]:
                        severity = "high"
                    elif vuln_type in ["hardcoded_secrets"]:
                        severity = "critical"
                    elif vuln_type in ["insecure_random"]:
                        severity = "low"

                    vulnerabilities.append({
                        "file": str(file_path),
                        "line": line_num,
                        "type": vuln_type,
                        "severity": severity,
                        "pattern": pattern,
                        "code": line.strip(),
                        "confidence": "medium",
                        "timestamp": datetime.now().isoformat()
                    })

    return vulnerabilities


def perform_static_security_analysis(scan_dirs: List[str] = None) -> List[Dict[str, Any]]:
    """Perform static security analysis on codebase."""
    if scan_dirs is None:
        scan_dirs = ["src"]

    all_vulnerabilities = []
    config = load_security_config()
    exclude_patterns = config.get("exclude_patterns", [])

    for scan_dir in scan_dirs:
        scan_path = _conf_dir.parent / scan_dir
        if not scan_path.exists():
            continue

        for file_path in scan_path.rglob("*.py"):
            # Check exclude patterns
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                vulnerabilities = scan_for_vulnerabilities(file_path, content)
                all_vulnerabilities.extend(vulnerabilities)

            except (IOError, UnicodeDecodeError):
                continue

    return all_vulnerabilities


def validate_input(input_value: str, input_type: str = "string") -> bool:
    """Validate input for security vulnerabilities."""
    if not isinstance(input_value, str):
        return False

    # Common attack patterns
    attack_patterns = [
        r"<script[^>]*>.*?</script>",  # XSS scripts
        r"javascript:",                # JavaScript URLs
        r"on\w+\s*=",                  # Event handlers
        r"';.*--",                     # SQL injection
        r";.*rm\s",                    # Command injection
        r"\.\./",                      # Path traversal
        r"%2e%2e%2f",                  # URL encoded path traversal
    ]

    for pattern in attack_patterns:
        if re.search(pattern, input_value, re.IGNORECASE):
            return False

    # Length limits based on type
    if input_type == "string" and len(input_value) > 1000:
        return False
    elif input_type == "email" and len(input_value) > 254:
        return False
    elif input_type == "url" and len(input_value) > 2000:
        return False

    return True


def run_security_assessment() -> Dict[str, Any]:
    """Run comprehensive security assessment."""
    # Perform static analysis
    static_vulns = perform_static_security_analysis()

    # Check dependencies
    try:
        dependency_vulns = check_dependencies_for_vulnerabilities()
    except ImportError:
        dependency_vulns = []

    all_vulnerabilities = static_vulns + dependency_vulns

    # Assess overall security posture
    assessment = assess_security_posture(all_vulnerabilities)

    # Calculate security score (0-100, higher is better)
    base_score = 100
    penalty_per_vuln = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
        "info": 1
    }

    total_penalty = 0
    severity_counts = assessment.get("severity_breakdown", {})

    for severity, count in severity_counts.items():
        penalty = penalty_per_vuln.get(severity, 1) * count
        total_penalty += penalty

    overall_score = max(0, base_score - total_penalty)

    return {
        "overall_score": overall_score,
        "vulnerabilities": all_vulnerabilities,
        "critical_count": severity_counts.get("critical", 0),
        "high_count": severity_counts.get("high", 0),
        "medium_count": severity_counts.get("medium", 0),
        "low_count": severity_counts.get("low", 0),
        "assessment": assessment,
        "scan_timestamp": datetime.now().isoformat()
    }


def check_dependencies_for_vulnerabilities() -> List[Dict[str, Any]]:
    """Check Python dependencies for known vulnerabilities."""
    vulnerabilities = []

    try:
        # Check if safety is available
        import safety
        result = subprocess.run(
            ["safety", "check", "--json"],
            capture_output=True,
            text=True,
            cwd=_conf_dir.parent,
            timeout=60
        )

        if result.returncode == 0:
            # Parse safety output
            safety_data = json.loads(result.stdout)
            for vuln in safety_data.get("vulnerabilities", []):
                vulnerabilities.append({
                    "file": "requirements.txt/dependencies",
                    "line": 0,
                    "type": "dependency_vulnerability",
                    "severity": "high" if vuln.get("severity") == "high" else "medium",
                    "package": vuln.get("package"),
                    "version": vuln.get("version"),
                    "vulnerability_id": vuln.get("vulnerability_id"),
                    "description": vuln.get("description"),
                    "confidence": "high",
                    "timestamp": datetime.now().isoformat()
                })

    except (ImportError, subprocess.TimeoutExpired, json.JSONDecodeError):
        # Fallback: basic requirements.txt scanning
        req_file = _conf_dir.parent / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Basic check for known vulnerable packages (simplified)
                            if any(pkg in line.lower() for pkg in ["django<3.2", "flask<2.0"]):
                                vulnerabilities.append({
                                    "file": str(req_file),
                                    "line": line_num,
                                    "type": "outdated_dependency",
                                    "severity": "medium",
                                    "package": line.split('==')[0] if '==' in line else line,
                                    "description": "Potentially outdated dependency",
                                    "confidence": "low",
                                    "timestamp": datetime.now().isoformat()
                                })
            except IOError:
                pass

    return vulnerabilities


def assess_security_posture(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Assess overall security posture based on vulnerabilities found."""
    config = load_security_config()
    threshold = config.get("severity_threshold", "medium")

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    total_score = 0

    for vuln in vulnerabilities:
        severity = vuln.get("severity", "info")
        severity_counts[severity] += 1
        total_score += SEVERITY_LEVELS.get(severity, 1)

    # Determine overall risk level
    if severity_counts["critical"] > 0 or total_score > 50:
        risk_level = "critical"
    elif severity_counts["high"] > 0 or total_score > 25:
        risk_level = "high"
    elif severity_counts["medium"] > 0 or total_score > 10:
        risk_level = "medium"
    elif total_score > 0:
        risk_level = "low"
    else:
        risk_level = "secure"

    # Check if security requirements are met
    threshold_met = True
    if threshold == "low" and risk_level in ["critical", "high", "medium"]:
        threshold_met = False
    elif threshold == "medium" and risk_level in ["critical", "high"]:
        threshold_met = False
    elif threshold == "high" and risk_level == "critical":
        threshold_met = False

    return {
        "risk_level": risk_level,
        "total_vulnerabilities": len(vulnerabilities),
        "severity_breakdown": severity_counts,
        "total_score": total_score,
        "threshold_met": threshold_met,
        "threshold": threshold,
        "assessment_timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def security_scanner():
    """Fixture to provide security scanning capabilities."""
    return SecurityScanner()


class SecurityScanner:
    """Helper class for security testing and vulnerability assessment."""

    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Scan a specific file for vulnerabilities."""
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return scan_for_vulnerabilities(path, content)
        except (IOError, UnicodeDecodeError):
            return []

    def scan_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Scan a directory for vulnerabilities."""
        return perform_static_security_analysis([directory])

    def check_dependencies(self) -> List[Dict[str, Any]]:
        """Check dependencies for vulnerabilities."""
        return check_dependencies_for_vulnerabilities()

    def assess_posture(self, vulnerabilities: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Assess security posture."""
        if vulnerabilities is None:
            vulnerabilities = perform_static_security_analysis() + check_dependencies_for_vulnerabilities()
        return assess_security_posture(vulnerabilities)

    def get_security_config(self) -> Dict[str, Any]:
        """Get current security configuration."""
        return load_security_config()

    def update_security_config(self, config: Dict[str, Any]):
        """Update security configuration."""
        current_config = load_security_config()
        current_config.update(config)
        save_security_config(current_config)


def pytest_addoption(parser):
    """Add security testing command line options."""
    group = parser.getgroup("security")

    group.addoption(
        "--security-scan",
        action="store_true",
        default=False,
        help="Perform security vulnerability scanning"
    )
    group.addoption(
        "--security-report",
        action="store_true",
        default=False,
        help="Generate detailed security assessment report"
    )
    group.addoption(
        "--fail-on-security",
        action="store_true",
        default=False,
        help="Fail tests if security vulnerabilities are found"
    )
    group.addoption(
        "--security-threshold",
        type=str,
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Security severity threshold (default: medium)"
    )


def pytest_sessionfinish(session, exitstatus):
    """Perform security assessment at session end if requested."""
    if session.config.getoption("--security-scan") or session.config.getoption("--security-report"):
        print("\n🔒 Performing Security Assessment...")

        # Perform comprehensive security scan
        static_vulns = perform_static_security_analysis()
        dependency_vulns = check_dependencies_for_vulnerabilities()
        all_vulnerabilities = static_vulns + dependency_vulns

        # Assess security posture
        assessment = assess_security_posture(all_vulnerabilities)

        # Save results
        report = {
            "assessment": assessment,
            "vulnerabilities": all_vulnerabilities,
            "scan_timestamp": datetime.now().isoformat(),
            "total_files_scanned": len(set(v["file"] for v in all_vulnerabilities if "file" in v))
        }
        save_vulnerability_report([report])

        # Display results
        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter:
            terminalreporter.write_sep("=", "Security Assessment Report")
            terminalreporter.write_line(f"Risk Level: {assessment['risk_level'].upper()}")
            terminalreporter.write_line(f"Total Vulnerabilities: {assessment['total_vulnerabilities']}")
            terminalreporter.write_line(f"Security Score: {assessment['total_score']}")

            severity_breakdown = assessment['severity_breakdown']
            terminalreporter.write_line("Severity Breakdown:")
            for severity, count in severity_breakdown.items():
                if count > 0:
                    terminalreporter.write_line(f"  {severity.capitalize()}: {count}")

            if not assessment['threshold_met']:
                terminalreporter.write_line(f"❌ Security threshold '{assessment['threshold']}' not met")
            else:
                terminalreporter.write_line(f"✅ Security requirements met")

            if all_vulnerabilities:
                terminalreporter.write_line("\nTop Vulnerabilities:")
                # Sort by severity
                sorted_vulns = sorted(all_vulnerabilities,
                                    key=lambda x: SEVERITY_LEVELS.get(x.get("severity", "info"), 1),
                                    reverse=True)
                for vuln in sorted_vulns[:5]:  # Show top 5
                    terminalreporter.write_line(f"  {vuln.get('severity', 'info').upper()}: {vuln.get('type')} in {vuln.get('file')}:{vuln.get('line')}")

            terminalreporter.write_line("")

    # Fail if security requirements not met and --fail-on-security specified
    if session.config.getoption("--fail-on-security"):
        reports = load_vulnerability_report()
        if reports:
            latest_report = reports[-1]
            assessment = latest_report.get("assessment", {})
            if not assessment.get("threshold_met", True):
                session.exitstatus = 1


def test_security_scanner_initialization():
    """Test that the security scanner can be initialized."""
    scanner = SecurityScanner()
    assert scanner is not None


def test_vulnerability_pattern_detection():
    """Test detection of common vulnerability patterns."""
    # Test SQL injection pattern
    sql_code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    vulnerabilities = scan_for_vulnerabilities("test.py", sql_code)

    assert len(vulnerabilities) > 0
    assert any(v["type"] == "sql_injection" for v in vulnerabilities)


def test_xss_pattern_detection():
    """Test detection of XSS vulnerability patterns."""
    xss_code = 'element.innerHTML = "<div>" + user_input + "</div>"'
    vulnerabilities = scan_for_vulnerabilities("test.py", xss_code)

    assert len(vulnerabilities) > 0
    assert any(v["type"] == "xss" for v in vulnerabilities)


def test_command_injection_detection():
    """Test detection of command injection vulnerabilities."""
    cmd_code = 'os.system("ls " + user_path)'
    vulnerabilities = scan_for_vulnerabilities("test.py", cmd_code)

    assert len(vulnerabilities) > 0
    assert any(v["type"] == "command_injection" for v in vulnerabilities)


def test_hardcoded_secrets_detection():
    """Test detection of hardcoded secrets."""
    secret_code = 'password = "secret123"'
    vulnerabilities = scan_for_vulnerabilities("test.py", secret_code)

    assert len(vulnerabilities) > 0
    assert any(v["type"] == "hardcoded_secrets" for v in vulnerabilities)


def test_input_validation():
    """Test input validation functionality."""
    # Test valid input
    assert validate_input("normal_string", "string") is True

    # Test SQL injection attempt
    assert validate_input("'; DROP TABLE users; --", "string") is False

    # Test XSS attempt
    assert validate_input("<script>alert('xss')</script>", "string") is False


def test_security_assessment_scoring():
    """Test security assessment scoring system."""
    # Test with no vulnerabilities
    assessment = assess_security_posture([])
    assert assessment["risk_level"] == "secure"
    assert assessment["total_score"] == 0
    assert assessment["threshold_met"] is True

    # Test with critical vulnerability
    critical_vuln = [{"severity": "critical", "type": "test"}]
    assessment = assess_security_posture(critical_vuln)
    assert assessment["risk_level"] == "critical"
    assert assessment["total_score"] > 0
    assert assessment["threshold_met"] is False


def test_dependency_vulnerability_check():
    """Test dependency vulnerability checking."""
    # This test may fail if safety is not installed, which is expected
    try:
        vulnerabilities = check_dependencies_for_vulnerabilities()
        assert isinstance(vulnerabilities, list)
    except ImportError:
        pytest.skip("Safety package not available for dependency checking")


def test_static_security_analysis():
    """Test static security analysis on codebase."""
    # Create a temporary test file with vulnerabilities
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('cursor.execute("SELECT * FROM users WHERE id = " + user_id)\n')
        f.write('password = "hardcoded_secret"\n')
        temp_file = f.name

    try:
        # Create a temporary directory structure
        temp_dir = Path(tempfile.mkdtemp())
        test_src = temp_dir / "src"
        test_src.mkdir()

        # Copy the test file to the temp src directory
        test_file = test_src / "vulnerable.py"
        test_file.write_text(Path(temp_file).read_text())

        # Run analysis
        vulnerabilities = perform_static_security_analysis([str(test_src.relative_to(temp_dir))])

        assert len(vulnerabilities) >= 2  # Should find SQL injection and hardcoded secret

    finally:
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_security_config_loading():
    """Test loading and saving security configuration."""
    config = load_security_config()
    assert isinstance(config, dict)
    assert "enabled_scanners" in config
    assert "severity_threshold" in config


def test_vulnerability_report_persistence():
    """Test saving and loading vulnerability reports."""
    test_report = {
        "assessment": {"risk_level": "low", "total_vulnerabilities": 1},
        "vulnerabilities": [{"type": "test", "severity": "low"}],
        "scan_timestamp": datetime.now().isoformat()
    }

    # Save report
    save_vulnerability_report([test_report])

    # Load reports
    reports = load_vulnerability_report()
    assert len(reports) > 0
    assert reports[-1]["assessment"]["risk_level"] == "low"


def test_run_security_assessment():
    """Test the main security assessment function."""
    results = run_security_assessment()
    assert isinstance(results, dict)
    assert "overall_score" in results
    assert "vulnerabilities" in results
    assert "critical_count" in results
    assert "high_count" in results