# Determinism Canonical Diff Report

- Baseline: run_1

## Diff: run_1 -> run_2 (lines changed: 102)
```diff
--- run_1
+++ run_2
@@ -199,13 +199,13 @@
     "canonical_data_summary": {
       "data_components": 11,
       "has_all_required_components": true,
-      "hash_input_size": 224050,
-      "total_files": 957
+      "hash_input_size": 224133,
+      "total_files": 958
     },
     "consistency_check": {
       "consistency_issues": [
         {
-          "description": "Structure file counts total (1328) doesn't match overall count (957)",
+          "description": "Structure file counts total (1331) doesn't match overall count (958)",
           "issue": "structure_file_count_mismatch",
           "severity": "medium"
         },
@@ -219,9 +219,9 @@
       "issues_found": 2,
       "overall_consistency": "medium"
     },
-    "determinism_hash": "075dbddf5a34f85f6d9a697e8fc3d9061536fc42909622ef01b4a7d6415077f6",
+    "determinism_hash": "1e04f552eb1d23639d6bb1a860b980ae023aa21a23fa517ade7b99331fe19434",
     "determinism_report": {
-      "analysis_hash": "075dbddf5a34f85f6d9a697e8fc3d9061536fc42909622ef01b4a7d6415077f6",
+      "analysis_hash": "1e04f552eb1d23639d6bb1a860b980ae023aa21a23fa517ade7b99331fe19434",
       "confidence_level": "medium",
       "consistency_score": 0.75,
       "description": "Analysis pipeline produces mostly deterministic results with minor inconsistencies",
@@ -748,7 +748,7 @@
         "risk_score": 0
       },
       "compliance_risk": {
-        "description": "Compliance risk: high (243 points)",
+        "description": "Compliance risk: high (247 points)",
         "risk_factors": [
           "critical_compliance_violations",
           "high_severity_compliance_violations",
@@ -928,7 +928,7 @@
           "/home/dee/workspace/AI/Repo-Scanner/src/core/pipeline/security_analysis/__init__.py"
         ],
         "critical_files_count": 17,
-        "critical_ratio": 0.017763845350052248,
+        "critical_ratio": 0.017745302713987474,
         "description": "Few critical files, most changes are safe",
         "safety_level": "high"
       },
@@ -942,7 +942,7 @@
       },
       "documentation_safety": {
         "description": "No documentation makes changes very risky",
-        "doc_coverage_ratio": 0.2571428571428571,
+        "doc_coverage_ratio": 0.2556818181818182,
         "doc_files_count": 45,
         "has_api_docs": false,
         "has_readme": false,
@@ -3809,11 +3809,11 @@
       "docs/ directory"
     ],
     "file_counts": {
-      "code": 175,
-      "config": 82,
+      "code": 176,
+      "config": 83,
       "docs": 45,
       "test": 69,
-      "total": 957
+      "total": 958
     },
     "frameworks": [
       "Maven (Java)",
@@ -3823,7 +3823,7 @@
       "Python (setup.py)"
     ],
     "languages": {
-      "JSON": 54,
+      "JSON": 55,
       "Java": 1,
       "JavaScript": 3,
       "Markdown": 39,
@@ -3839,7 +3839,7 @@
     ]
   },
   "summary": {
-    "files_scanned": 957,
+    "files_scanned": 958,
     "gaps_count": 0,
     "overall_score": 0.0,
     "tests_discovered": 69
@@ -3849,8 +3849,8 @@
     "test_coverage_signals": {
       "coverage_tools": [],
       "has_coverage_tools": false,
-      "test_file_percentage": 28.278688524590162,
-      "test_to_code_ratio": 0.3942857142857143,
+      "test_file_percentage": 28.163265306122447,
+      "test_to_code_ratio": 0.39204545454545453,
       "untested_modules": [
         "/home/dee/workspace/AI/Repo-Scanner/enhanced_scanner/baseline_assessment.py",
         "/home/dee/workspace/AI/Repo-Scanner/scripts/assess_operational_readiness.py",
```

## Diff: run_1 -> run_3 (lines changed: 102)
```diff
--- run_1
+++ run_3
@@ -199,13 +199,13 @@
     "canonical_data_summary": {
       "data_components": 11,
       "has_all_required_components": true,
-      "hash_input_size": 224050,
-      "total_files": 957
+      "hash_input_size": 224213,
+      "total_files": 959
     },
     "consistency_check": {
       "consistency_issues": [
         {
-          "description": "Structure file counts total (1328) doesn't match overall count (957)",
+          "description": "Structure file counts total (1334) doesn't match overall count (959)",
           "issue": "structure_file_count_mismatch",
           "severity": "medium"
         },
@@ -219,9 +219,9 @@
       "issues_found": 2,
       "overall_consistency": "medium"
     },
-    "determinism_hash": "075dbddf5a34f85f6d9a697e8fc3d9061536fc42909622ef01b4a7d6415077f6",
+    "determinism_hash": "4f823915deb764b87d58fe86d6e345dcd95c959b1a0e1fa40ebe96d558dfd769",
     "determinism_report": {
-      "analysis_hash": "075dbddf5a34f85f6d9a697e8fc3d9061536fc42909622ef01b4a7d6415077f6",
+      "analysis_hash": "4f823915deb764b87d58fe86d6e345dcd95c959b1a0e1fa40ebe96d558dfd769",
       "confidence_level": "medium",
       "consistency_score": 0.75,
       "description": "Analysis pipeline produces mostly deterministic results with minor inconsistencies",
@@ -748,7 +748,7 @@
         "risk_score": 0
       },
       "compliance_risk": {
-        "description": "Compliance risk: high (243 points)",
+        "description": "Compliance risk: high (251 points)",
         "risk_factors": [
           "critical_compliance_violations",
           "high_severity_compliance_violations",
@@ -928,7 +928,7 @@
           "/home/dee/workspace/AI/Repo-Scanner/src/core/pipeline/security_analysis/__init__.py"
         ],
         "critical_files_count": 17,
-        "critical_ratio": 0.017763845350052248,
+        "critical_ratio": 0.017726798748696558,
         "description": "Few critical files, most changes are safe",
         "safety_level": "high"
       },
@@ -942,7 +942,7 @@
       },
       "documentation_safety": {
         "description": "No documentation makes changes very risky",
-        "doc_coverage_ratio": 0.2571428571428571,
+        "doc_coverage_ratio": 0.2542372881355932,
         "doc_files_count": 45,
         "has_api_docs": false,
         "has_readme": false,
@@ -3809,11 +3809,11 @@
       "docs/ directory"
     ],
     "file_counts": {
-      "code": 175,
-      "config": 82,
+      "code": 177,
+      "config": 84,
       "docs": 45,
       "test": 69,
-      "total": 957
+      "total": 959
     },
     "frameworks": [
       "Maven (Java)",
@@ -3823,7 +3823,7 @@
       "Python (setup.py)"
     ],
     "languages": {
-      "JSON": 54,
+      "JSON": 56,
       "Java": 1,
       "JavaScript": 3,
       "Markdown": 39,
@@ -3839,7 +3839,7 @@
     ]
   },
   "summary": {
-    "files_scanned": 957,
+    "files_scanned": 959,
     "gaps_count": 0,
     "overall_score": 0.0,
     "tests_discovered": 69
@@ -3849,8 +3849,8 @@
     "test_coverage_signals": {
       "coverage_tools": [],
       "has_coverage_tools": false,
-      "test_file_percentage": 28.278688524590162,
-      "test_to_code_ratio": 0.3942857142857143,
+      "test_file_percentage": 28.04878048780488,
+      "test_to_code_ratio": 0.3898305084745763,
       "untested_modules": [
         "/home/dee/workspace/AI/Repo-Scanner/enhanced_scanner/baseline_assessment.py",
         "/home/dee/workspace/AI/Repo-Scanner/scripts/assess_operational_readiness.py",
```
