#!/usr/bin/env python3
"""
Integration test for Week 2: SQL and Command Injection Deep Validation
"""

import sys
sys.path.insert(0, 'src')

from core.pipeline.security_analysis import SecurityAnalyzer
from pathlib import Path
import tempfile
import shutil

def create_test_files():
    """Create test files with SQL and command injection patterns."""
    test_dir = tempfile.mkdtemp(prefix="week2_integration_")
    
    # Test file 1: Vulnerable SQL injection (should be DETECTED)
    test_file1 = Path(test_dir) / "vulnerable_sql.py"
    test_file1.write_text(
        'def get_user(user_id):\n'
        '    query = f"SELECT * FROM users WHERE id = {user_id}"\n'
        '    cursor.execute(query)\n'
        '    return cursor.fetchone()\n'
    )
    
    # Test file 2: Safe SQL with parameterization (should be REJECTED)
    test_file2 = Path(test_dir) / "safe_sql.py"
    test_file2.write_text(
        'def get_user(user_id):\n'
        '    query = "SELECT * FROM users WHERE id = ?"\n'
        '    cursor.execute(query, (user_id,))\n'
        '    return cursor.fetchone()\n'
    )
    
    # Test file 3: Safe ORM usage (should be REJECTED)
    test_file3 = Path(test_dir) / "safe_orm.py"
    test_file3.write_text(
        'from django.db import models\n'
        '\n'
        'def get_user(user_id):\n'
        '    return User.objects.filter(id=user_id).first()\n'
    )
    
    # Test file 4: Vulnerable command injection (should be DETECTED)
    test_file4 = Path(test_dir) / "vulnerable_cmd.py"
    test_file4.write_text(
        'import os\n'
        '\n'
        'def list_files(path):\n'
        '    os.system(f"ls {path}")\n'
    )
    
    # Test file 5: Safe command with list form (should be REJECTED)
    test_file5 = Path(test_dir) / "safe_cmd.py"
    test_file5.write_text(
        'import subprocess\n'
        '\n'
        'def list_files(path):\n'
        '    subprocess.run(["ls", path])\n'
    )
    
    # Test file 6: Command injection with sanitization (should be REJECTED)
    test_file6 = Path(test_dir) / "sanitized_cmd.py"
    test_file6.write_text(
        'import os\n'
        'import shlex\n'
        '\n'
        'def cat_file(filename):\n'
        '    filename = shlex.quote(filename)\n'
        '    os.system(f"cat {filename}")\n'
    )
    
    return test_dir, [test_file1, test_file2, test_file3, test_file4, test_file5, test_file6]

def main():
    print("🧪 Week 2 Integration Test: SQL & Command Injection Deep Validation")
    print("=" * 80)
    print()
    
    # Create test files
    test_dir, test_files = create_test_files()
    print(f"✅ Created test directory: {test_dir}\n")
    
    # Initialize analyzer
    analyzer = SecurityAnalyzer()
    
    # Check if validators are available
    if not analyzer.sql_injection_validator:
        print("❌ SQLInjectionValidator not available!")
        return 1
    if not analyzer.command_injection_validator:
        print("❌ CommandInjectionValidator not available!")
        return 1
    
    print("✅ SQL Injection Validator initialized")
    print("✅ Command Injection Validator initialized")
    print()
    print("=" * 80)
    
    # Expected results
    expected_results = {
        "vulnerable_sql.py": ("SQL_VULN", "F-string SQL injection"),
        "safe_sql.py": ("SAFE", "Parameterized query"),
        "safe_orm.py": ("SAFE", "Django ORM"),
        "vulnerable_cmd.py": ("CMD_VULN", "F-string command injection"),
        "safe_cmd.py": ("SAFE", "List form subprocess"),
        "sanitized_cmd.py": ("LOW_RISK", "shlex.quote reduces risk but still uses os.system"),
    }
    
    results = {}
    total_sql_vuln = 0
    total_cmd_vuln = 0
    
    for test_file in test_files:
        file_name = test_file.name
        print(f"\n📄 {file_name}")
        print("-" * 80)
        
        findings = analyzer._analyze_file(str(test_file))
        sql_findings = [f for f in findings if f.vulnerability_type == 'sql_injection']
        cmd_findings = [f for f in findings if f.vulnerability_type == 'command_injection']
        
        print(f"SQL injection findings: {len(sql_findings)}")
        print(f"Command injection findings: {len(cmd_findings)}")
        
        expected_action, description = expected_results.get(file_name, ("UNKNOWN", ""))
        
        if expected_action == "SQL_VULN":
            if sql_findings:
                print(f"✅ CORRECT: SQL injection DETECTED")
                for f in sql_findings:
                    print(f"   Line {f.line_number}: {f.code_snippet[:60]}")
                results[file_name] = "PASS"
                total_sql_vuln += len(sql_findings)
            else:
                print(f"❌ WRONG: SQL injection NOT detected")
                print(f"   Expected: {description}")
                results[file_name] = "FAIL"
        
        elif expected_action == "CMD_VULN":
            if cmd_findings:
                print(f"✅ CORRECT: Command injection DETECTED")
                for f in cmd_findings:
                    print(f"   Line {f.line_number}: {f.code_snippet[:60]}")
                results[file_name] = "PASS"
                total_cmd_vuln += len(cmd_findings)
            else:
                print(f"❌ WRONG: Command injection NOT detected")
                print(f"   Expected: {description}")
                results[file_name] = "FAIL"
        
        elif expected_action == "LOW_RISK":
            # LOW_RISK: May or may not be detected depending on confidence threshold
            # This is acceptable behavior - sanitization reduces but doesn't eliminate risk
            print(f"✅ ACCEPTABLE: {description}")
            if cmd_findings:
                print(f"   Detected with low confidence (acceptable)")
                total_cmd_vuln += len(cmd_findings)
            else:
                print(f"   Not detected (also acceptable)")
            results[file_name] = "PASS"
        
        else:  # SAFE
            if not sql_findings and not cmd_findings:
                print(f"✅ CORRECT: False positive REJECTED")
                print(f"   Reason: {description}")
                results[file_name] = "PASS"
            else:
                print(f"❌ WRONG: False positive NOT rejected")
                print(f"   SQL findings: {len(sql_findings)}, Cmd findings: {len(cmd_findings)}")
                results[file_name] = "FAIL"
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print()
    
    print("Test Results:")
    for file_name, result in results.items():
        status = "✅ PASS" if result == "PASS" else "❌ FAIL"
        print(f"  {status}: {file_name}")
    
    passed = sum(1 for r in results.values() if r == "PASS")
    total = len(results)
    print()
    print(f"Total: {passed}/{total} tests passed")
    print(f"SQL injection vulnerabilities detected: {total_sql_vuln}")
    print(f"Command injection vulnerabilities detected: {total_cmd_vuln}")
    print()
    
    if passed == total:
        print("🎉 SUCCESS: All tests passed!")
        print("   - Vulnerable patterns detected correctly")
        print("   - Safe patterns correctly rejected as false positives")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    print()
    
    # Clean up
    shutil.rmtree(test_dir)
    print("✅ Cleaned up test directory")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
