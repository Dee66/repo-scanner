#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/home/dee/workspace/AI/Repo-Scanner/src')

print("Starting test...")

from core.pipeline.security_analysis import analyze_security_vulnerabilities
from adapters.language_adapter_manager import LanguageAdapterManager

print("Imported function...")

# Debug: check adapter
adapter_manager = LanguageAdapterManager()
file_path = '/home/dee/workspace/AI/Repo-Scanner/test_unsafe.py'
adapter = adapter_manager.get_adapter_for_file(file_path)
print(f"Adapter for {file_path}: {adapter}")
print(f"Adapter type: {type(adapter)}")
print(f"Adapter language: {adapter.language_name if adapter else 'None'}")
print(f"Adapter parser: {adapter.parser if adapter else 'None'}")
print(f"Adapter language obj: {adapter.language if adapter else 'None'}")

# Test adapter directly
if adapter:
    ast_result = adapter.extract_ast(file_path)
    print(f"AST result unsafe_patterns: {ast_result.get('unsafe_patterns', [])}")

# Test replicating the function logic
print("Replicating function logic...")
unsafe_patterns = {
    "summary": {
        "total_patterns": 0,
        "high_severity": 0,
        "medium_severity": 0,
        "low_severity": 0,
        "languages_covered": 0
    },
    "patterns_by_language": {},
    "critical_findings": []
}

languages_processed = set()

file_path = '/home/dee/workspace/AI/Repo-Scanner/test_unsafe.py'
adapter = adapter_manager.get_adapter_for_file(file_path)

if adapter:
    print(f"Processing {file_path} with {adapter}")
    try:
        ast_result = adapter.extract_ast(file_path)
        file_unsafe_patterns = ast_result.get("unsafe_patterns", [])
        print(f"Got {len(file_unsafe_patterns)} patterns")
        
        if file_unsafe_patterns:
            language = adapter.language_name
            languages_processed.add(language)
            print(f"Language: {language}")

            if language not in unsafe_patterns["patterns_by_language"]:
                unsafe_patterns["patterns_by_language"][language] = []

            unsafe_patterns["patterns_by_language"][language].append({
                "file_path": file_path,
                "language": language,
                "patterns": file_unsafe_patterns
            })

            for pattern in file_unsafe_patterns:
                severity = pattern.get("severity", "low")
                unsafe_patterns["summary"]["total_patterns"] += 1
                print(f"Added pattern: {pattern['type']}, total now {unsafe_patterns['summary']['total_patterns']}")

                if severity == "high":
                    unsafe_patterns["summary"]["high_severity"] += 1
                    unsafe_patterns["critical_findings"].append({
                        "file_path": file_path,
                        "pattern_type": pattern.get("type", "Unknown"),
                        "severity": severity,
                        "description": pattern.get("description", "No description"),
                        "line": pattern.get("line", 0)
                    })

    except Exception as e:
        print(f"Exception: {e}")

print(f"Final total: {unsafe_patterns['summary']['total_patterns']}")

# Test the security analysis
file_list = ['/home/dee/workspace/AI/Repo-Scanner/test_unsafe.py']
semantic_analysis = {}  # Empty for now

print(f"Calling analyze_security_vulnerabilities with file_list: {file_list}")

result = analyze_security_vulnerabilities(file_list, semantic_analysis)

print("Security analysis result:")
print(f"Total patterns: {result['unsafe_patterns']['summary']['total_patterns']}")
print(f"High severity: {result['unsafe_patterns']['summary']['high_severity']}")
print(f"Patterns by language: {result['unsafe_patterns']['patterns_by_language']}")
print(f"Critical findings: {result['unsafe_patterns']['critical_findings']}")
